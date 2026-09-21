const chartInstances = new Map();

export function destroyChart(key) {
  const existing = chartInstances.get(key);
  if (existing) {
    existing.destroy();
    chartInstances.delete(key);
  }
}

export function destroyAllCharts() {
  for (const key of [...chartInstances.keys()]) {
    destroyChart(key);
  }
}

export function renderCategoryDonut(canvas, breakdown, totalSpend) {
  destroyChart("category-donut");
  const positive = breakdown.filter((item) => Number(item.amount) > 0);
  if (!canvas || positive.length === 0 || Number(totalSpend) <= 0) {
    return null;
  }
  const chart = new Chart(canvas, {
    type: "doughnut",
    data: {
      labels: positive.map((item) => item.category),
      datasets: [
        {
          data: positive.map((item) => Number(item.amount)),
          backgroundColor: [
            "#4f46e5",
            "#3525cd",
            "#006e4b",
            "#565e74",
            "#bec6e0",
            "#6ffbbe",
            "#ba1a1a",
            "#dae2fd",
            "#3323cc",
            "#777587",
          ],
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: "bottom" } },
    },
  });
  chartInstances.set("category-donut", chart);
  return chart;
}

export function renderLineChart(key, canvas, labels, datasets) {
  destroyChart(key);
  if (!canvas) return null;
  const chart = new Chart(canvas, {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
    },
  });
  chartInstances.set(key, chart);
  return chart;
}

export function renderBarChart(key, canvas, labels, datasets) {
  destroyChart(key);
  if (!canvas) return null;
  const chart = new Chart(canvas, {
    type: "bar",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { x: { stacked: false }, y: { beginAtZero: true } },
    },
  });
  chartInstances.set(key, chart);
  return chart;
}
