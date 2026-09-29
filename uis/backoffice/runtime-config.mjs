let configPromise;

export function loadPublicConfig() {
  if (!configPromise) {
    configPromise = fetch(new URL("./.env.local", import.meta.url), { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) return {};
        const values = {};
        const contents = await response.text();
        for (const line of contents.split(/\r?\n/)) {
          const match = line.match(/^\s*(NEXT_PUBLIC_[A-Z0-9_]+)\s*=\s*(.*?)\s*$/);
          if (match) values[match[1]] = match[2].replace(/^(['"])(.*)\1$/, "$2");
        }
        return values;
      })
      .catch(() => ({}));
  }
  return configPromise;
}