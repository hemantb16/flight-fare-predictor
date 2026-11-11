// Progressive enhancements for the search form. Everything also works without JS.
(function () {
  const $ = (id) => document.getElementById(id);
  const origin = $("origin");
  const destination = $("destination");
  const airline = $("airline");
  const cabin = $("cabin");
  const travel = $("travel_date");
  const routeHint = $("route-hint");
  const daysHint = $("days-hint");
  if (!origin || !destination) return;

  const allAirlines = airline ? [...airline.options].map((o) => ({ value: o.value, text: o.text })) : [];

  $("swap").addEventListener("click", () => {
    [origin.value, destination.value] = [destination.value, origin.value];
    refreshRoute();
  });

  // Select the whole value on focus so typing a new city is quick.
  for (const input of [origin, destination]) {
    input.addEventListener("focus", () => input.select());
    input.addEventListener("change", refreshRoute);
  }

  function setAirlines(routeAirlines) {
    if (!airline) return;
    const current = airline.value;
    const list = routeAirlines
      ? [{ value: "any", text: "Any airline" }].concat(
          routeAirlines.map((a) => ({
            value: a.code,
            text: a.name + (a.stops.includes(0) ? " · non-stop" : " · via hub"),
          }))
        )
      : allAirlines;
    airline.replaceChildren(...list.map((o) => new Option(o.text, o.value)));
    airline.value = list.some((o) => o.value === current) ? current : "any";
  }

  function setCabins(available) {
    if (!cabin) return;
    for (const opt of cabin.options) opt.disabled = available ? !available.includes(opt.value) : false;
    if (cabin.selectedOptions[0] && cabin.selectedOptions[0].disabled) cabin.value = "economy";
  }

  let pending;
  async function refreshRoute() {
    const params = new URLSearchParams({ origin: origin.value, destination: destination.value });
    const token = (pending = Symbol());
    try {
      const res = await fetch("/api/route?" + params);
      const data = await res.json();
      if (token !== pending) return;
      // Normalise "hamburg" or "bkk" to the full "Hamburg (HAM)" label.
      if (data.origin_label && document.activeElement !== origin) origin.value = data.origin_label;
      if (data.destination_label && document.activeElement !== destination) destination.value = data.destination_label;
      if (!data.airlines.length) {
        routeHint.textContent = data.distance_km ? "No airline in our network flies this route." : "";
        setAirlines(null);
        setCabins(null);
        return;
      }
      const n = data.airlines.length;
      routeHint.textContent =
        data.distance_km.toLocaleString("en") + " km · " + n + " airline" + (n === 1 ? "" : "s") +
        " · " + (data.nonstop ? "non-stop available" : "connections only");
      setAirlines(data.airlines);
      setCabins(data.cabins);
    } catch (_) {
      routeHint.textContent = "";
    }
  }

  function updateDays() {
    if (!travel || !daysHint) return;
    const t = new Date(travel.value + "T00:00");
    if (Number.isNaN(t.getTime())) return (daysHint.textContent = "");
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const days = Math.round((t - today) / 86400000);
    daysHint.textContent = days === 0 ? "Today" : days === 1 ? "Tomorrow" : days > 1 ? "In " + days + " days" : "";
  }

  travel && travel.addEventListener("input", updateDays);
  updateDays();
  refreshRoute();
})();
