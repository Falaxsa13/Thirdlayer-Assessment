// Configuration from environment variables with defaults
export const config = {
  // API endpoint for sending interactions
  apiEndpoint: import.meta.env.VITE_API_ENDPOINT || "http://localhost:3000/api/interactions",
  
  // Ring buffer size (max events stored in memory)
  ringBufferSize: parseInt(import.meta.env.VITE_RING_BUFFER_SIZE || "2000"),
  
  // Number of interactions to send to API (should be <= buffer size)
  apiExportSize: parseInt(import.meta.env.VITE_API_EXPORT_SIZE || "1000"),
};

console.log("[Config] Loaded configuration:", config);