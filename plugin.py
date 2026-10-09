# -*- coding: utf-8 -*-
"""
<plugin key="SkodaMySkoda" name="Škoda MyŠkoda Public API" author="OpenAI" version="0.7.0" wikilink="" externallink="https://public.api.connect.skoda-auto.cz/docs">
    <description>
        <h2>Škoda MyŠkoda Public API v0.6</h2>
        <p>Read-only vehicle telemetry from the official Škoda Public API.</p>
        <p>Range and odometer use legacy-compatible Custom Sensors.</p>
    </description>
    <params>
        <param field="Mode1" label="Polling interval (seconds)" width="120px" default="300" type="number" min="60" max="3600" step="60"/>
        <param field="Mode2" label="Škoda API key" width="350px" required="true" password="true"/>
        <param field="Mode3" label="VIN" width="250px" required="true"/>
        <param field="Mode4" label="Debug logging">
            <options>
                <option label="No" value="No" default="true"/>
                <option label="Yes" value="Yes"/>
            </options>
        </param>
    </params>
</plugin>
"""

import Domoticz
import json
import time
import threading
import requests

BASE_URL = "https://public.api.connect.skoda-auto.cz/api/v1/vehicles"


class BasePlugin:
    def __init__(self):
        self.enabled = False
        self.api_key = ""
        self.vin = ""
        self.poll_seconds = 300
        self.debug = False
        self.last_poll = 0
        self.busy = False

    def onStart(self):
        self.enabled = True
        self.api_key = Parameters.get("Mode2", "").strip()
        self.vin = Parameters.get("Mode3", "").strip().upper()

        try:
            self.poll_seconds = int(Parameters.get("Mode1", "300"))
        except Exception:
            self.poll_seconds = 300
        self.poll_seconds = max(60, self.poll_seconds)
        self.debug = Parameters.get("Mode4", "No") == "Yes"

        Domoticz.Log("Škoda MyŠkoda API v0.7 gestart")
        Domoticz.Log("VIN: " + (self.vin if self.vin else "<niet ingesteld>"))
        Domoticz.Log("Polling: %d seconden" % self.poll_seconds)

        if not self.api_key:
            Domoticz.Error("Geen Škoda API key ingesteld")
        if not self.vin:
            Domoticz.Error("Geen VIN ingesteld")

        self.create_devices()

        if self.api_key and self.vin:
            self.last_poll = time.time()
            self.busy = True
            threading.Thread(target=self.poll_api, daemon=True).start()

    def onStop(self):
        self.enabled = False
        Domoticz.Log("Škoda MyŠkoda API gestopt")

    def onHeartbeat(self):
        if not self.enabled or self.busy:
            return
        if time.time() - self.last_poll < self.poll_seconds:
            return
        if not self.api_key or not self.vin:
            return

        self.last_poll = time.time()
        self.busy = True
        threading.Thread(target=self.poll_api, daemon=True).start()

    def create_devices(self):
        # v0.5 heeft Units 2 en 3 al correct als Custom Sensor aangemaakt.
        # v0.6 verwijdert niets meer, zodat bestaande waarden/logs behouden blijven.
        definitions = [
            (1, "Battery", "Percentage"),
            (2, "Range", "Custom Sensor"),
            (3, "Odometer", "Custom Sensor"),
            (4, "Charge Power", "Usage"),
            (5, "Charge Limit", "Percentage"),
            (6, "Charge State", "Text"),
            (7, "Plug", "Text"),
            (8, "Air Conditioning", "Text"),
            (9, "Target Temperature", "Temperature"),
            (10, "Doors Locked", "Text"),
            (11, "Doors", "Text"),
            (12, "Windows", "Text"),
            (13, "Lights", "Text"),
            (14, "Trunk", "Text"),
            (15, "Bonnet", "Text"),
            (16, "Parking", "Text"),
        ]

        for unit, name, typename in definitions:
            if unit in Devices:
                continue
            try:
                if unit in (2, 3):
                    Domoticz.Device(
                        Name=name,
                        Unit=unit,
                        Type=243,
                        Subtype=31,
                        Switchtype=0,
                        Options={"Custom": "1;km"},
                        Used=1
                    ).Create()
                else:
                    Domoticz.Device(
                        Name=name,
                        Unit=unit,
                        TypeName=typename,
                        Used=1
                    ).Create()
            except Exception as exc:
                Domoticz.Error(
                    "Kon device '%s' niet maken: %s" % (name, exc)
                )

    def poll_api(self):
        try:
            url = BASE_URL + "/" + self.vin
            headers = {
                "X-API-Key": self.api_key,
                "Accept": "application/json",
                "User-Agent": "Domoticz-Skoda-MySkoda/0.7",
            }

            response = requests.get(url, headers=headers, timeout=20)

            if self.debug:
                Domoticz.Log("Škoda HTTP status: %d" % response.status_code)

            if response.status_code != 200:
                if response.status_code == 401:
                    Domoticz.Error("Škoda API 401: API key ongeldig of verlopen")
                elif response.status_code == 403:
                    Domoticz.Error("Škoda API 403: API key niet geautoriseerd voor deze VIN")
                elif response.status_code == 429:
                    Domoticz.Error(
                        "Škoda API 429: rate limit overschreden; Retry-After=%s"
                        % response.headers.get("Retry-After", "?")
                    )
                else:
                    Domoticz.Error(
                        "Škoda API HTTP %d: %s"
                        % (response.status_code, response.text[:300])
                    )
                return

            data = response.json()
            vehicle = data.get("vehicle", data)

            if self.debug:
                Domoticz.Log(
                    "Škoda API ontvangen (%d bytes)" % len(response.text)
                )

            self.update_devices(vehicle)

            if self.debug:
                Domoticz.Log(
                    "Škoda rate limit: remaining=%s reset=%s key-expires=%s"
                    % (
                        response.headers.get("RateLimit-Remaining", "?"),
                        response.headers.get("RateLimit-Reset", "?"),
                        response.headers.get("X-API-Key-Expires-At", "?"),
                    )
                )

        except requests.RequestException as exc:
            Domoticz.Error("Škoda API request mislukt: %s" % exc)
        except Exception as exc:
            Domoticz.Error("Škoda plugin fout: %s" % exc)
        finally:
            self.busy = False

    def update_text(self, unit, value):
        if unit in Devices and value is not None:
            Devices[unit].Update(nValue=0, sValue=str(value))

    def update_numeric(self, unit, value, decimals=0):
        if unit not in Devices or value is None:
            return
        try:
            value = float(value)
            text = str(int(round(value))) if decimals == 0 else ("%.*f" % (decimals, value)).rstrip("0").rstrip(".")
            Devices[unit].Update(nValue=0, sValue=text)
        except Exception as exc:
            if self.debug:
                Domoticz.Log("Numerieke update mislukt unit %d: %s" % (unit, exc))

    def find_key(self, obj, wanted):
        """Recursively find a key, case-insensitive, in nested API JSON."""
        wanted = wanted.lower()
        if isinstance(obj, dict):
            for key, value in obj.items():
                if str(key).lower() == wanted:
                    return value
            for value in obj.values():
                result = self.find_key(value, wanted)
                if result is not None:
                    return result
        elif isinstance(obj, list):
            for value in obj:
                result = self.find_key(value, wanted)
                if result is not None:
                    return result
        return None

    def first_key(self, obj, keys):
        for key in keys:
            value = self.find_key(obj, key)
            if value is not None:
                return value
        return None

    def as_number(self, value):
        try:
            if isinstance(value, dict):
                value = value.get("value", value.get("amount"))
            return float(value)
        except Exception:
            return None

    def range_km(self, vehicle):
        # Official response uses remaining cruising range in meters.
        raw = self.first_key(vehicle, [
            "remainingCruisingRangeInMeters",
            "rangeInMeters",
            "remainingRangeInMeters",
        ])
        number = self.as_number(raw)
        if number is not None:
            return number / 1000.0

        # Some API representations expose the range directly in km.
        raw = self.first_key(vehicle, [
            "range",
            "remainingRange",
            "cruisingRange",
        ])
        number = self.as_number(raw)
        if number is not None:
            # Values such as 294000 are clearly meters.
            return number / 1000.0 if number > 2000 else number
        return None

    def odometer_km(self, vehicle):
        raw = self.first_key(vehicle, [
            "mileageInKm",
            "odometerInKm",
            "odometer",
            "mileage",
        ])
        number = self.as_number(raw)
        if number is None:
            return None
        # If an endpoint ever returns meters, normalize to km.
        return number / 1000.0 if number > 1000000 else number

    def update_custom_km(self, unit, value):
        """Legacy Domoticz Custom Sensor: nValue=0, numeric value in sValue."""
        if unit not in Devices or value is None:
            return
        try:
            km = float(value)
            text = str(int(round(km)))
            Devices[unit].Update(nValue=0, sValue=text)
            if self.debug:
                Domoticz.Log("Škoda unit %d = %s km" % (unit, text))
        except Exception as exc:
            Domoticz.Error("Custom km update mislukt unit %d: %s" % (unit, exc))

    def update_devices(self, v):
        # Values are deliberately found by key rather than assuming one fixed
        # nesting level. This keeps v0.6 compatible with the response shape
        # returned by the user's current MyŠkoda API endpoint.
        soc = self.first_key(v, [
            "stateOfChargeInPercent",
            "batteryLevelInPercent",
            "soc",
        ])
        self.update_numeric(1, soc)

        range_km = self.range_km(v)
        self.update_custom_km(2, range_km)

        odo_km = self.odometer_km(v)
        self.update_custom_km(3, odo_km)

        charge_kw = self.first_key(v, [
            "chargePowerInKw",
            "chargingPowerInKw",
        ])
        charge_kw = self.as_number(charge_kw)
        if charge_kw is not None:
            self.update_numeric(4, charge_kw * 1000.0)

        charge_limit = self.first_key(v, [
            "targetStateOfChargeInPercent",
            "targetSocInPercent",
        ])
        self.update_numeric(5, charge_limit)

        charge_state = self.first_key(v, ["state", "chargingState"])
        plug_state = self.first_key(v, ["plugConnectionState", "plugState"])
        if charge_state is not None:
            self.update_text(6, charge_state)
        if plug_state is not None:
            self.update_text(7, plug_state)

        ac_state = self.first_key(v, ["airConditioningState"])
        if ac_state is None:
            ac = v.get("airConditioning", {}) if isinstance(v, dict) else {}
            ac_state = ac.get("state") if isinstance(ac, dict) else None
        self.update_text(8, ac_state)

        target_temp = self.first_key(v, ["targetTemperature"])
        target_temp = self.as_number(target_temp)
        self.update_numeric(9, target_temp, 1)

        # Status fields
        for unit, keys in [
            (10, ["reliableLockStatus", "doorsLocked"]),
            (11, ["doors"]),
            (12, ["windows"]),
            (13, ["lights"]),
            (14, ["trunk"]),
            (15, ["bonnet"]),
        ]:
            value = self.first_key(v, keys)
            if value is not None and not isinstance(value, (dict, list)):
                self.update_text(unit, value)

        address = self.first_key(v, ["formattedAddress"])
        if address:
            self.update_text(16, address)
        else:
            parking = v.get("parkingPosition", {}) if isinstance(v, dict) else {}
            gps = parking.get("gpsCoordinates", {}) if isinstance(parking, dict) else {}
            if isinstance(gps, dict) and gps.get("latitude") is not None and gps.get("longitude") is not None:
                self.update_text(16, "%.6f, %.6f" % (gps["latitude"], gps["longitude"]))

        if self.debug:
            Domoticz.Log(
                "Škoda update: SOC=%s range=%s km odometer=%s km charge=%s kW"
                % (soc, range_km, odo_km, charge_kw)
            )


global _plugin
_plugin = BasePlugin()

def onStart():
    _plugin.onStart()

def onStop():
    _plugin.onStop()

def onHeartbeat():
    _plugin.onHeartbeat()
