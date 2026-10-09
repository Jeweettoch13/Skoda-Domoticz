Škoda MyŠkoda Domoticz plugin v0.7

Fix voor oudere Domoticz-versies.

Belangrijkste wijziging:
- Alle Device.Update() calls gebruiken alleen nValue en sValue.
- Log=True is verwijderd, omdat oudere Domoticz Python plugins dit argument niet accepteren.
- Range en Odometer blijven Custom Sensor Type 243 / Subtype 31.
- Range wordt omgerekend van meters naar km.
- Odometer wordt als km weergegeven.
- Bestaande devices worden niet verwijderd.

Met de bekende API-response verwacht:
- Range: 294 km
- Odometer: 26907 km

Installatie:
1. Stop het Škoda hardware/plugin-item in Domoticz.
2. Vervang de pluginbestanden door deze versie.
3. Start Domoticz opnieuw.
4. API key en VIN hetzelfde laten.

De oude Domoticz-versie accepteert:
Devices[unit].Update(nValue=0, sValue="294")

en niet:
Devices[unit].Update(..., Log=True)
