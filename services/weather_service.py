"""天气服务：Open-Meteo 异步请求 + 本地缓存 + WMO 代码映射。

全异步（QNetworkAccessManager），请求期间不阻塞 UI；任何网络/解析失败
都只更新状态文案并回退到缓存，绝不弹窗。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from app import constants as C


class WeatherService(QObject):
    """天气数据门面：updated() 表示缓存/状态变化，界面据此刷新副行。"""

    updated = Signal()
    status_changed = Signal()

    def __init__(self, settings, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._network = QNetworkAccessManager(self)
        self._reply: QNetworkReply | None = None
        self._stage = ""
        self._resolved: dict | None = None
        self._offline = False
        self._status = "未设置城市，副行显示 --°"
        self._cache = self._load_cache()

        self._timer = QTimer(self)
        self._timer.setInterval(C.WEATHER_REFRESH_MS)
        self._timer.timeout.connect(self.refresh)

    # ------------------------------------------------------------ 生命周期
    def start(self) -> None:
        if not self._settings.data.show_weather:
            return
        self._timer.start()
        if self._settings.data.weather_city.strip():
            self.refresh()
        else:
            self._set_status("未设置城市，副行显示 --°")

    def stop(self) -> None:
        self._timer.stop()
        self._abort()

    def set_enabled(self, enabled: bool) -> None:
        if enabled:
            self.start()
        else:
            self.stop()
            self._set_status("天气已关闭")
        self.updated.emit()

    # ------------------------------------------------------------ 城市
    def set_city(self, city: str) -> None:
        city = (city or "").strip()
        self._settings.set("weather_city", city)
        if not city:
            self._resolved = None
            self._set_status("未设置城市，副行显示 --°")
            self.updated.emit()
            return
        self.refresh()

    # ------------------------------------------------------------ 请求
    def refresh(self) -> None:
        if not self._settings.data.show_weather:
            return
        city = self._settings.data.weather_city.strip()
        if not city:
            self._set_status("未设置城市，副行显示 --°")
            self.updated.emit()
            return
        self._abort()
        query = urlencode({"name": city, "count": 1, "language": "zh", "format": "json"})
        self._stage = "geocode"
        self._set_status("正在获取天气…")
        reply = self._network.get(self._build_request(f"{C.GEOCODE_URL}?{query}"))
        self._reply = reply
        reply.finished.connect(lambda r=reply: self._on_geocode_finished(r))

    def _forecast(self, latitude: float, longitude: float) -> None:
        query = urlencode(
            {
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,weather_code",
                "timezone": "auto",
            }
        )
        self._stage = "forecast"
        self._set_status("正在获取天气…")
        reply = self._network.get(self._build_request(f"{C.FORECAST_URL}?{query}"))
        self._reply = reply
        reply.finished.connect(lambda r=reply: self._on_forecast_finished(r))

    def _build_request(self, url: str) -> QNetworkRequest:
        request = QNetworkRequest(QUrl(url))
        request.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, C.WEATHER_USER_AGENT)
        request.setAttribute(
            QNetworkRequest.Attribute.CacheLoadControlAttribute,
            QNetworkRequest.CacheLoadControl.AlwaysNetwork,
        )
        try:
            request.setTransferTimeout(C.WEATHER_TIMEOUT_MS)
        except AttributeError:
            pass
        return request

    def _on_geocode_finished(self, reply: QNetworkReply) -> None:
        if reply is not self._reply:
            reply.deleteLater()
            return
        self._release_reply(reply)
        if reply.error() != QNetworkReply.NetworkError.NoError:
            self._on_failure()
            return
        payload = self._read_json(reply)
        results = (payload or {}).get("results") or []
        if not results:
            self._offline = self._has_temperature()
            self._set_status("未找到该城市")
            self.updated.emit()
            return
        first = results[0]
        latitude = first.get("latitude")
        longitude = first.get("longitude")
        if latitude is None or longitude is None:
            self._on_failure()
            return
        self._resolved = {
            "name": first.get("name") or self._settings.data.weather_city,
            "admin": first.get("admin1") or "",
            "country": first.get("country") or "",
            "latitude": round(float(latitude), 2),
            "longitude": round(float(longitude), 2),
        }
        self._forecast(float(latitude), float(longitude))

    def _on_forecast_finished(self, reply: QNetworkReply) -> None:
        if reply is not self._reply:
            reply.deleteLater()
            return
        self._release_reply(reply)
        if reply.error() != QNetworkReply.NetworkError.NoError:
            self._on_failure()
            return
        payload = self._read_json(reply)
        current = (payload or {}).get("current") or {}
        temperature = current.get("temperature_2m")
        if temperature is None:
            self._on_failure()
            return
        code = current.get("weather_code")
        self._cache = {
            "city": self._settings.data.weather_city,
            "resolved": self._resolved,
            "temperature": float(temperature),
            "weather_code": int(code) if code is not None else 0,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        self._offline = False
        self._save_cache()
        self._set_status("天气已更新")
        self.updated.emit()

    def _on_failure(self) -> None:
        self._offline = self._has_temperature()
        if self._offline:
            self._set_status("网络异常，正在显示缓存数据")
        else:
            self._set_status("网络异常，暂无天气数据（副行显示 --°）")
        self.updated.emit()

    def _release_reply(self, reply: QNetworkReply) -> None:
        self._reply = None
        reply.deleteLater()

    def _abort(self) -> None:
        if self._reply is not None:
            reply = self._reply
            self._reply = None
            try:
                reply.abort()
            except RuntimeError:
                pass
            reply.deleteLater()

    @staticmethod
    def _read_json(reply: QNetworkReply) -> dict | None:
        try:
            raw = bytes(reply.readAll()).decode("utf-8", "replace")
            data = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            return None
        return data if isinstance(data, dict) else None

    # ------------------------------------------------------------ 展示
    def summary(self) -> str:
        """主窗口副行文本：符号 + 温度（可带离线标记）。"""
        if not self._settings.data.show_weather:
            return ""
        temperature = self._cache.get("temperature")
        if temperature is None:
            return C.WEATHER_EMPTY_SUMMARY
        symbol = C.WMO_CODES.get(int(self._cache.get("weather_code", -1)), C.WMO_UNKNOWN)[0]
        text = f"{symbol} {int(round(float(temperature)))}°"
        return text + (C.WEATHER_OFFLINE_SUFFIX if self._offline else "")

    def description(self) -> str:
        """当前天气中文描述，供设置面板回显。"""
        temperature = self._cache.get("temperature")
        if temperature is None:
            return "暂无数据"
        label = C.WMO_CODES.get(int(self._cache.get("weather_code", -1)), C.WMO_UNKNOWN)[1]
        return f"{label} {round(float(temperature))}°"

    def resolved_text(self) -> str:
        resolved = self._resolved or (self._cache.get("resolved") or None)
        if not resolved:
            return "尚未解析坐标"
        parts = [str(resolved.get("name") or "")]
        if resolved.get("admin"):
            parts.append(str(resolved["admin"]))
        if resolved.get("country"):
            parts.append(str(resolved["country"]))
        name = " ".join(part for part in parts if part).strip() or "未知城市"
        return f"{name}（{resolved.get('latitude')}, {resolved.get('longitude')}）"

    def last_updated_text(self) -> str:
        stamp = self._cache.get("updated_at")
        if not stamp:
            return "尚未获取"
        try:
            moment = datetime.fromisoformat(str(stamp))
        except ValueError:
            return str(stamp)
        return moment.strftime("%m-%d %H:%M")

    def status_text(self) -> str:
        return self._status

    def _set_status(self, text: str) -> None:
        if text != self._status:
            self._status = text
            self.status_changed.emit()

    def _has_temperature(self) -> bool:
        return self._cache.get("temperature") is not None

    # ------------------------------------------------------------ 缓存
    def _load_cache(self) -> dict:
        path: Path = C.weather_cache_file()
        try:
            data = json.loads(path.read_text("utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _save_cache(self) -> None:
        path: Path = C.weather_cache_file()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self._cache, ensure_ascii=False, indent=2), "utf-8")
        except OSError:
            pass
