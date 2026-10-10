Škoda MyŠkoda Domoticz plugin v0.7

Škoda provides a MyŠkoda Public API that lets owners and developers access vehicle data and control functions for free without a business registration or developer account.

Key Features of the Official API

• Vehicle Status: Check doors, windows, lights, and GPS parking positions.
• Driving & Fuel Data: View odometer readings, fuel levels, or battery charge and range.
• Climate & Remote Commands: Control air conditioning, auxiliary heating, ventilation, and start or stop charging.
• Smart Home Integration: Designed for platforms like Home Assistant and energy management tools like evcc.

How It Works & Limits

• Authentication: Generate an access token directly inside version 8.16 (or newer) of the MyŠkoda app.
• Cost: Free to use (no credit card or NDA required).
• Limits: Maximum of 5 API keys per vehicle, with a rate limit of 20 requests per hour per vehicle.



Step 1: Generate your API Key

1. Open the MyŠkoda App on your smartphone (ensure you are on version 8.16 or newer).
2. Navigate to your Account Settings / Profile.
3. Look for the Developer / Public API section.
4. Generate a new token. Note down the API Key (passed via headers) and check its expiration date.
5. Grab your vehicle's VIN (Vehicle Identification Number) from the app or your car's windshield.

Step 2: Fill in the forms of API and VIN in the Domoticz plugin.

Step 3: Sensors are made trough devices.
