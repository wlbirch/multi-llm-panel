exports.onExecutePostLogin = async (event, api) => {
  const expectedClientId = "tpc_iKn5ici4rntzLKwybBVh6b";
  const expectedAudience = "https://crossllm-mcp.onrender.com/mcp";

  if (
    event.client.client_id === expectedClientId &&
    event.resource_server?.identifier === expectedAudience
  ) {
    api.accessToken.addScope("run:panel");
  }
};
