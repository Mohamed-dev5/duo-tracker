const ME = window.ME;
const DATA = window.DAYS_DATA; // { side: { "day": seconds } }

const fmt = (s) => {
  const h = String(Math.floor(s / 3600)).padStart(2, "0");
  const m = String(Math.floor((s % 3600) / 60)).padStart(2, "0");
  const sec = String(s % 60).padStart(2, "0");
  return `${h}:${m}:${sec}`;
};

const human = (s) => {
  if (!s) return "no time yet";
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  return [h && `${h}h`, m && `${m}m`, (sec || (!h && !m)) && `${sec}s`].filter(Boolean).join(" ");
};

// ---------- calendars + timers ----------
document.querySelectorAll(".side").forEach((el) => {
  const side = el.dataset.side;
  const mine = el.dataset.mine === "true";
  const info = el.querySelector(".day-info");
  const clock = el.querySelector(".clock");
  const timerDay = el.querySelector(".timer-day");
  const startBtn = el.querySelector(".start");
  const stopBtn = el.querySelector(".stop");
  const dayBtns = el.querySelectorAll(".day");

  let selected = null;
  let running = false;
  let startedAt = 0;
  let tick = null;

  const show = (day) => {
    info.textContent = `Day ${day}: ${human(DATA[side][day] || 0)}`;
  };

  dayBtns.forEach((b) => {
    b.addEventListener("click", () => {
      const day = b.dataset.day;
      show(day);
      if (!mine || running) return; // can't switch day while running
      selected = day;
      dayBtns.forEach((x) => x.classList.toggle("selected", x === b));
      timerDay.textContent = `Timer for day ${day}`;
    });
  });

  if (!mine) return;

  const render = () => {
    clock.textContent = fmt(Math.floor((Date.now() - startedAt) / 1000));
  };

  startBtn.addEventListener("click", () => {
    if (!selected) {
      timerDay.textContent = "Pick a day first!";
      return;
    }
    running = true;
    startedAt = Date.now();
    startBtn.disabled = true;
    stopBtn.disabled = false;
    tick = setInterval(render, 250);
    render();
  });

  stopBtn.addEventListener("click", async () => {
    clearInterval(tick);
    const seconds = Math.floor((Date.now() - startedAt) / 1000);
    running = false;
    startBtn.disabled = false;
    stopBtn.disabled = true;
    clock.textContent = "00:00:00"; // reset
    if (seconds < 1) return;
    const res = await fetch(`/api/days/${side}/${selected}/add`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ seconds }),
    });
    if (res.ok) {
      const j = await res.json();
      DATA[side][selected] = j.seconds;
      el.querySelector(`.day[data-day="${selected}"]`).classList.add("done");
      show(selected);
    } else {
      info.textContent = "Could not save time, try again.";
    }
  });
});

// ---------- shared sources ----------
const list = document.getElementById("links");
const form = document.getElementById("link-form");
const err = document.getElementById("link-error");

const renderLink = (l) => {
  const li = document.createElement("li");
  li.className = l.side;
  const a = document.createElement("a");
  a.href = l.url;
  a.target = "_blank";
  a.rel = "noopener noreferrer";
  a.textContent = l.title;
  const who = document.createElement("small");
  who.textContent = l.side;
  li.append(a, who);
  if (l.side === ME) {
    const del = document.createElement("button");
    del.type = "button";
    del.textContent = "×";
    del.title = "Delete";
    del.addEventListener("click", async () => {
      const r = await fetch(`/api/links/${l.id}`, { method: "DELETE" });
      if (r.ok) li.remove();
    });
    li.append(del);
  }
  return li;
};

async function loadLinks() {
  const r = await fetch("/api/links");
  if (!r.ok) return;
  list.replaceChildren(...(await r.json()).map(renderLink));
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  err.textContent = "";
  const url = document.getElementById("link-url");
  const title = document.getElementById("link-title");
  const r = await fetch("/api/links", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url: url.value, title: title.value }),
  });
  if (r.ok) {
    list.prepend(renderLink(await r.json()));
    url.value = "";
    title.value = "";
  } else {
    err.textContent = "Invalid link.";
  }
});

loadLinks();
setInterval(loadLinks, 15000); // see the other side's new links
