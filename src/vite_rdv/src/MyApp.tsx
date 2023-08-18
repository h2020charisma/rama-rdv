import React from 'react';
import { App,  H5GroveProvider } from '@h5web/app';
import '@h5web/app/dist/styles.css';

const URL = 'https://api.ramanchada.ideaconsult.net/h5grove';
const FILE_DEFAULT = 'e7e9918a-85ea-4551-a31c-b40327aba8af.nxs';

function getQueryParam(name : string) {
  const urlSearchParams = new URLSearchParams(window.location.search);
  return urlSearchParams.get(name);
}

function MyApp() {
  const uuid = getQueryParam('uuid');
  const FILEPATH = uuid ? `${uuid}.nxs` : FILE_DEFAULT;
  return (
    <H5GroveProvider
      url={URL}
      filepath={FILEPATH}
      axiosConfig={{ params: { file: FILEPATH } }}
    >
      <App />
    </H5GroveProvider>
  );

}

export default MyApp;