import { App, MockProvider } from '@h5web/app';
import '@h5web/app/dist/styles.css';

function MyApp() {
  return (
    <MockProvider>
      <App explorerOpen={false} />
    </MockProvider>
  );
}

export default MyApp;