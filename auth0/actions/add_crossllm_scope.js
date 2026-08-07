exports.onExecutePostLogin = async (event, api) => {
  const expectedClientId = "tpc_iKn5ici4rntzLKwybBVh6b";

  if (event.client.client_id === expectedClientId) {
    api.accessToken.addScope("run:panel");
  }
};
