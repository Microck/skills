---
name: usage-phone-widget
description: Build or update iPhone home screen widgets (ScriptWidget SWT packages) that show remaining usage, balances, and reset times for AI subscriptions and other metered services in one place.
---

# Usage phone widget

1. **Scope the change.** Inspect the current widget, manifest, and data contract. Use a separate widget ID and package for a new view. For an authorized update, keep the target ID and bump its version. A bar or layout change requires updated JSX in the imported widget. Keep unrelated widgets, endpoints, and services out of the change.

2. **Verify the source and identity.** Run the provider's native usage command noninteractively under the collector's login, or use its authenticated usage or billing endpoint. Examples include Antigravity `agy -p /usage --output-format json`, OMP `usage --provider … --json` for Codex and SuperGrok, `colab --auth adc usage`, and the Mistral Vibe billing budget. Confirm the account and any relevant workspace or plan before labeling a row, especially for personal versus work logins. Treat ambiguous identity, missing fields, and failed reads as unavailable. Keep provider credentials on the host.

3. **Serve a background snapshot.** ScriptWidget has a five-second execution limit for the entire script, including networking and rendering. Give the widget one fast HTTPS read. Collect with bounded timeouts outside the request handler, record freshness, and atomically publish the cache with per-source status. A working pattern collects every two minutes and returns HTTP 503 when the snapshot is missing or more than 15 minutes old. Show stale or unavailable states explicitly. Measure the cache read with enough headroom for the phone's network and rendering.

4. **Keep access private.** Use a private HTTPS route such as Tailscale and a dedicated, revocable read-only widget bearer token in the Authorization header. Keep server token and cache files owner-only. Use placeholders in reusable source and exports. If a personal SWT embeds a bearer token, handle the whole ZIP as a credential and keep it out of commits, public uploads, logs, and chat. Rotate it if exposed.

5. **Render what the source supports.** Fill the bar with remaining quota. Full means available and empty means exhausted. Use a reported remaining fraction directly, or subtract used percent from 100 once. Show a raw balance without a bar when the allowance is unknown. Label any requested estimate and its basis, and keep it distinct from verified quota. Combine only comparable values with known allowances, such as Vibe balances converted to a common currency using a known exchange rate. Label a partial aggregate “Known total”. Show window reset time separately from saved reset credits. Read the inventory for the same account and display its available count and next expiry when reported. Missing inventory stays unknown, and refresh never redeems credits.

6. **Keep rows compact.** Group each label, remaining value, bar, and reset text in one compact vertical stack, using a known-good device-rendered widget as the spacing baseline. If SwiftUI distributes extra vertical space between rows, test a bottom spacer to absorb it; verify the result on the phone before calling it fixed.

7. **Package and verify.** ZIP `widget.json` and `main.jsx` at the archive root with a `.swt` extension. Match a known-good export for the target runtime. Known-good exports use `formatVersion: 2`, `runtimeVersion: "1.0"`, `entry: "main.jsx"`, and `supportedFamilies: ["systemLarge"]`. For a networked widget use `permissions: ["network"]` and put only the endpoint hostname in `networkDomains`. Check the ZIP, manifest, and JSX, then exercise fresh, stale, and unavailable data plus full and empty bars. When device access is authorized, import into ScriptWidget, grant the declared network access, select the intended script and widget size, and confirm refresh and layout on the iPhone over the intended network. Record which checks ran. A desktop preview cannot verify the iPhone runtime.

8. **Walk the user through the phone setup.** Finish by giving the user these steps, in plain language, for the package you built. This skill cannot install the app or place the widget for them.
   1. Install ScriptWidget from the App Store.
   2. Send the `.swt` to the iPhone with AirDrop, iCloud Drive, or email. Open it, tap Share, and choose ScriptWidget.
   3. Review the import and allow the network access it asks for.
   4. Touch and hold the Home Screen, tap Edit, then Add Widget. Pick ScriptWidget and the Large size.
   5. Tap the new widget (or touch and hold it and choose Edit Widget) and select the imported script.
   Importing alone does not put anything on the Home Screen. If the widget shows an unavailable state, the phone cannot reach your snapshot over the private network yet; have the user connect to it and wait for the next refresh.
