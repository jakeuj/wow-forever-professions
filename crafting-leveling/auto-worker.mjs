import { searchRoute } from './auto-search.mjs';

self.addEventListener('message', ({ data }) => {
  const { catalog, profession, input, snapshot, seeds, components } = data;
  try {
    const result = searchRoute(catalog, profession, input, snapshot, {
      seeds, components, progress: update => self.postMessage({ type: 'progress', ...update }),
    });
    self.postMessage({ type: 'complete', result });
  } catch (error) {
    self.postMessage({ type: 'error', message: error.message });
  }
});
