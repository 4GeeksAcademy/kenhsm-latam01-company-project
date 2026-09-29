export function mountApp(selector, render) {
  const root = document.querySelector(selector);

  if (root) {
    root.innerHTML = render();
  }
}