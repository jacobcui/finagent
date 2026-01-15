const BASE_URL = 'http://localhost:8000';

function renderJSON(el, data) {
  el.textContent = JSON.stringify(data, null, 2);
}

async function fetchFinancialData(e) {
  e.preventDefault();
  const asset = document.getElementById('fetch-asset').value.trim();
  const start = document.getElementById('fetch-start').value;
  const end = document.getElementById('fetch-end').value;
  const out = document.getElementById('fetch-result');

  const url = new URL('/fetch-financial-data', BASE_URL);
  url.searchParams.set('asset_symbol', asset);
  url.searchParams.set('start_date', start);
  url.searchParams.set('end_date', end);

  out.textContent = 'Loading...';
  try {
    const res = await fetch(url.toString());
    const data = await res.json();
    renderJSON(out, data);
  } catch (err) {
    renderJSON(out, { error: String(err) });
  }
}

async function getTradingDecision(e) {
  e.preventDefault();
  const asset = document.getElementById('dec-asset').value.trim();
  const news = document.getElementById('dec-news').value;
  const guidance = document.getElementById('dec-guidance').value;
  const price = document.getElementById('dec-price').value;
  const useReal = document.getElementById('dec-real').checked;
  const image = document.getElementById('dec-image').files[0];
  const out = document.getElementById('decision-result');

  const form = new FormData();
  form.set('asset_symbol', asset);
  if (news) form.set('news_text', news);
  if (guidance) form.set('expert_guidance', guidance);
  if (price) form.set('price_data', price);
  if (image) form.set('kline_image', image);

  const url = new URL('/trade/decision', BASE_URL);
  url.searchParams.set('use_real_data', useReal ? 'true' : 'false');

  out.textContent = 'Loading...';
  try {
    const res = await fetch(url.toString(), { method: 'POST', body: form });
    const data = await res.json();
    renderJSON(out, data);
  } catch (err) {
    renderJSON(out, { error: String(err) });
  }
}

window.addEventListener('DOMContentLoaded', () => {
  document.getElementById('fetch-form').addEventListener('submit', fetchFinancialData);
  document.getElementById('decision-form').addEventListener('submit', getTradingDecision);
});
