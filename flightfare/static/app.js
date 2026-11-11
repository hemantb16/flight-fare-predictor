// Small progressive enhancements for the search form. The form works without JS.
(function () {
  const origin = document.getElementById("origin");
  const destination = document.getElementById("destination");
  const swap = document.getElementById("swap");
  const airline = document.getElementById("airline");
  const cabin = document.getElementById("cabin");
  const travel = document.getElementById("travel_date");
  const booking = document.getElementById("booking_date");
  const daysBefore = document.getElementById("days-before");

  if (swap && origin && destination) {
    swap.addEventListener("click", () => {
      [origin.value, destination.value] = [destination.value, origin.value];
    });
  }

  // Only enable cabin classes the selected airline actually sells.
  // On first load an invalid choice is left alone so its error stays visible.
  function syncCabins(adjust) {
    if (!airline || !cabin) return;
    const offered = airline.selectedOptions[0].dataset.cabins.split(",");
    for (const opt of cabin.options) opt.disabled = !offered.includes(opt.value);
    if (adjust && cabin.selectedOptions[0].disabled) cabin.value = offered[0];
  }

  function updateDaysBefore() {
    if (!travel || !booking || !daysBefore) return;
    const t = Date.parse(travel.value);
    const b = Date.parse(booking.value);
    if (Number.isNaN(t) || Number.isNaN(b)) {
      daysBefore.textContent = "";
      return;
    }
    const days = Math.round((t - b) / 86400000);
    daysBefore.textContent = days >= 0 ? `${days} day${days === 1 ? "" : "s"} before departure` : "";
    travel.min = booking.value;
  }

  airline && airline.addEventListener("change", () => syncCabins(true));
  travel && travel.addEventListener("input", updateDaysBefore);
  booking && booking.addEventListener("input", updateDaysBefore);
  syncCabins(false);
  updateDaysBefore();
})();
