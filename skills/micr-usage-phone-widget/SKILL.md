---
name: micr-usage-phone-widget
description: Build or update iPhone home screen widgets (ScriptWidget SWT packages) that show remaining usage, balances, and reset times for AI subscriptions and other metered services in one place.
---

# Usage phone widget

1. **Ask what the widget should show.** Before building anything, ask the user, in plain language and only for what you cannot find yourself:
   - Which services and accounts to include, and how to tell accounts apart (for example a personal and a work login on the same service).
   - What to show for each: amount left, percent used, a money balance, when the limit resets, or something else.
   - How they check it today: an app or website, a command they run, or an account page. This points to where the numbers can come from.
   - Which machine can stay on to collect the numbers, and how the phone can reach it.
   - How many widgets and which sizes. Default to one Large widget unless they want more.
   Confirm a short plan (rows, values, data source per row) before writing code. For an update to an existing widget, inspect its manifest, JSX, and data contract instead, keep its ID, and bump its version.

2. **Find a reliable source for each row.** Prefer, in order: the service's own usage or billing API, its official command-line tool run noninteractively with machine-readable output, then a documented account page. Avoid scraping a logged-in dashboard unless the user accepts that it may break. Run each source once and show the user what came back. Confirm which account, workspace, or plan it reports before labeling the row. Treat an ambiguous account, missing fields, or a failed read as unavailable, never as zero. Keep the service's credentials on the collecting machine; the phone never gets them.

3. **Serve one small snapshot.** ScriptWidget gives the whole script a short time budget for networking and rendering, so the widget should make one fast HTTPS request and nothing else. Read the enforced limits from `$runtime` and stay well under them. On the collecting machine, gather every source on a timer with bounded timeouts, outside the request handler, and atomically write one JSON snapshot with a timestamp and a status per source. Serve that file. Return an error the widget can recognize when the snapshot is missing or too old, and pick the refresh and staleness intervals with the user. Measure the request from the phone's network.

4. **Keep access private.** Reach the snapshot over a private route (a VPN or mesh network such as Tailscale) when the user has one. Otherwise put it behind HTTPS with a dedicated, revocable, read-only token sent in the Authorization header. Keep token and snapshot files readable only by their owner. Use placeholders in any source you share. A `.swt` that embeds a token is a credential: keep it out of commits, public uploads, logs, and chat, and rotate the token if it leaks.

5. **Show only what the source supports.** For a limited allowance, fill the bar with what is left: full means available, empty means used up. Use a reported remaining fraction as is, or subtract a used percent from 100 once. When the allowance is unknown, show the raw number without a bar. Label any estimate and what it is based on, and keep it visually distinct from reported values. Combine values into a total only when they share a unit and have known allowances, and label a total with gaps "Known total". Show the time until a limit resets separately from any stored credits or top-ups, and leave missing data as unknown. Refreshing the widget must never spend or redeem anything.

6. **Lay it out for a glance.** Give each row its label, the remaining value, its bar, and its reset time in one compact vertical group. Fit the user's rows to the chosen size, and offer a second widget rather than cramming. Show fresh, stale, and unavailable states so they read differently at a glance. If SwiftUI spreads rows apart, try a bottom spacer to absorb the extra space, and check the result on the phone.

7. **Package and verify.** ZIP `widget.json` and `main.jsx` at the archive root with a `.swt` extension, matching a known-good export for the user's ScriptWidget version. A typical manifest has `formatVersion: 2`, `runtimeVersion: "1.0"`, `entry: "main.jsx"`, and `supportedFamilies` set to the chosen sizes. For a networked widget add `permissions: ["network"]` and list only the snapshot's hostname in `networkDomains`. Check the ZIP, manifest, and JSX, then try fresh, stale, and unavailable snapshots plus full and empty bars. A desktop preview cannot prove the iPhone result; say which checks you ran and which still need the phone.

8. **Walk the user through the phone setup.** Finish by giving the user these steps for the package you built. You cannot install the app or place the widget for them.
   1. Install ScriptWidget from the App Store.
   2. Send the `.swt` to the iPhone with AirDrop, iCloud Drive, or email. Open it, tap Share, and choose ScriptWidget.
   3. Review the import and allow the network access it asks for.
   4. Touch and hold the Home Screen, tap Edit, then Add Widget. Pick ScriptWidget and the size you built for.
   5. Tap the new widget (or touch and hold it and choose Edit Widget) and select the imported script.
   Importing alone does not put anything on the Home Screen. If the widget shows as unavailable, the phone cannot reach the snapshot yet; have the user check the private network or address and wait for the next refresh.
