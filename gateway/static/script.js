const api = (path, opts) => fetch(`/api/${path}`, {
  headers: { "Content-Type": "application/json" },
  ...opts,
}).then(r => r.json());

async function refreshAll() {
  const authors = await api("authors");
  renderList("author-list", authors, a => `${a.id}. ${a.full_name} (${a.country || "—"})`, "authors");

  const books = await api("books");
  renderList("book-list", books, b => `${b.id}. ${b.title} [${b.copies_available}/${b.copies_total}] — автор ${b.author_id}`, "books");

  const members = await api("members");
  renderList("member-list", members, m => `${m.id}. ${m.full_name} <${m.email}>`, "members");

  const loans = await api("loans");
  renderList("loan-list", loans, l => `${l.id}. книга ${l.book_id} → читатель ${l.member_id} ${l.returned_at ? "(возвращена)" : ""}`, "loans");
}

function renderList(elementId, items, labelFn, resource) {
  const ul = document.getElementById(elementId);
  ul.innerHTML = "";
  items.forEach(item => {
    const li = document.createElement("li");
    li.textContent = labelFn(item);
    const del = document.createElement("button");
    del.textContent = "✕";
    del.onclick = async () => {
      await api(`${resource}/${item.id}`, { method: "DELETE" });
      refreshAll();
    };
    li.appendChild(del);
    ul.appendChild(li);
  });
}

function bindForm(formId, resource, transform) {
  document.getElementById(formId).addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target).entries());
    await api(resource, { method: "POST", body: JSON.stringify(transform ? transform(data) : data) });
    e.target.reset();
    refreshAll();
  });
}

bindForm("author-form", "authors");
bindForm("book-form", "books", d => ({ ...d, year: Number(d.year) || null, copies_total: Number(d.copies_total) || 1, author_id: Number(d.author_id) }));
bindForm("member-form", "members");
bindForm("loan-form", "loans", d => ({ book_id: Number(d.book_id), member_id: Number(d.member_id) }));

refreshAll();
