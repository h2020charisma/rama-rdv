import { App, MockProvider } from '@h5web/app';
import '@h5web/app/dist/styles.css';

function MyApp() {


  return (
    <MockProvider>
      <App  />
    </MockProvider>
  );

}

export default MyApp;