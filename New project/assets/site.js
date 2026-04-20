async function loadCompanies() {
  const response = await fetch("/data/companies.json");
  if (!response.ok) {
    throw new Error("Unable to load company data.");
  }
  return response.json();
}

function createCard(company, index, template) {
  const fragment = template.content.cloneNode(true);
  const link = fragment.querySelector('[data-role="link"]');
  const title = fragment.querySelector('[data-role="title"]');
  const location = fragment.querySelector('[data-role="location"]');
  const overview = fragment.querySelector('[data-role="overview"]');
  const image = fragment.querySelector('[data-role="image"]');
  const article = fragment.querySelector(".company-card");

  article.style.animationDelay = `${index * 55}ms`;
  link.href = `/companies/${company.slug}/`;
  title.textContent = company.title;
  location.textContent = company.location;
  overview.textContent = company.overview || "Open the one-pager, download the PDF page, and scan its dedicated QR code.";
  image.src = company.image_path;
  image.alt = `${company.title} one-pager`;

  return fragment;
}

function renderCompanies(companies) {
  const grid = document.querySelector("#company-grid");
  const template = document.querySelector("#company-card-template");
  const count = document.querySelector("#company-count");
  const search = document.querySelector("#company-search");

  function paint(items) {
    grid.innerHTML = "";
    items.forEach((company, index) => {
      grid.appendChild(createCard(company, index, template));
    });
    count.textContent = String(items.length);
  }

  paint(companies);

  search.addEventListener("input", () => {
    const query = search.value.trim().toLowerCase();
    if (!query) {
      paint(companies);
      return;
    }

    const filtered = companies.filter((company) => {
      const haystack = `${company.title} ${company.location} ${company.overview}`.toLowerCase();
      return haystack.includes(query);
    });
    paint(filtered);
  });
}

loadCompanies()
  .then((payload) => {
    renderCompanies(payload.companies);
  })
  .catch((error) => {
    const grid = document.querySelector("#company-grid");
    grid.innerHTML = `<p>${error.message}</p>`;
  });
