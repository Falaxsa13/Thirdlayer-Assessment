import { useState, useEffect } from "react";
import { browser } from "wxt/browser";
import { config } from "../../src/config";
import "./App.css";

interface InteractionEvent {
  id: string;
  type: string;
  timestamp: number;
  tabId?: number;
  windowId?: number;
  url?: string;
  title?: string;
  payload?: any;
}

function App() {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string>("");
  const [eventCount, setEventCount] = useState<number>(0);
  const [interactions, setInteractions] = useState<InteractionEvent[]>([]);
  const [showDetails, setShowDetails] = useState(false);

  // Fetch interactions on mount and periodically
  useEffect(() => {
    fetchInteractions();
    const interval = setInterval(fetchInteractions, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchInteractions = async () => {
    try {
      const response = await browser.runtime.sendMessage({
        type: "get-recent-interactions",
        limit: config.apiExportSize,
      });
      const fetchedInteractions = response?.interactions || [];
      setInteractions(fetchedInteractions);
      setEventCount(fetchedInteractions.length);
      console.log(
        `Fetched ${fetchedInteractions.length} interactions (max: ${config.apiExportSize})`
      );
    } catch (error) {
      console.error("Error fetching interactions:", error);
    }
  };

  const sendInteractions = async () => {
    setLoading(true);
    setStatus("Sending interactions to API...");

    try {
      // Send to API using config
      const apiResponse = await fetch(config.apiEndpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          events: interactions,
          timestamp: Date.now(),
        }),
      });

      if (apiResponse.ok) {
        setStatus(`✅ Successfully sent ${interactions.length} interactions!`);
      } else {
        setStatus(`❌ Failed to send interactions: ${apiResponse.statusText}`);
      }
    } catch (error) {
      console.error("Error sending interactions:", error);
      setStatus(
        `❌ Error: ${error instanceof Error ? error.message : "Unknown error"}`
      );
    } finally {
      setLoading(false);
    }
  };

  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  const getEventIcon = (type: string) => {
    switch (type) {
      case "page-load":
        return "📄";
      case "click":
        return "👆";
      case "type":
        return "⌨️";
      case "copy":
        return "📋";
      case "paste":
        return "📌";
      case "highlight":
        return "🖍️";
      case "tab-switch":
        return "🔄";
      case "tab-removal":
        return "❌";
      default:
        return "•";
    }
  };

  return (
    <div style={{ padding: "20px", minWidth: "400px", maxWidth: "600px" }}>
      <h2>Interaction Logger</h2>

      <div
        style={{
          marginBottom: "15px",
          padding: "10px",
          backgroundColor: "#f8f9fa",
          borderRadius: "5px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span style={{ fontWeight: "bold" }}>
          {eventCount} interactions tracked
        </span>
        <button
          onClick={() => setShowDetails(!showDetails)}
          style={{
            padding: "5px 10px",
            fontSize: "12px",
            cursor: "pointer",
            background: "transparent",
            border: "1px solid #ccc",
            borderRadius: "3px",
          }}
        >
          {showDetails ? "Hide" : "Show"} Details
        </button>
      </div>

      <div className="card">
        <button
          onClick={sendInteractions}
          disabled={loading || interactions.length === 0}
          style={{
            padding: "10px 20px",
            fontSize: "16px",
            cursor:
              loading || interactions.length === 0 ? "not-allowed" : "pointer",
            opacity: loading || interactions.length === 0 ? 0.6 : 1,
            width: "100%",
          }}
        >
          {loading ? "Sending..." : `Send ${interactions.length} Interactions`}
        </button>

        {status && (
          <div
            style={{
              marginTop: "15px",
              padding: "10px",
              backgroundColor: "#f0f0f0",
              borderRadius: "5px",
              fontSize: "14px",
            }}
          >
            {status}
          </div>
        )}
      </div>

      {showDetails && (
        <div
          style={{
            marginTop: "20px",
            maxHeight: "400px",
            overflowY: "auto",
            border: "1px solid #ddd",
            borderRadius: "5px",
            padding: "10px",
          }}
        >
          <h3 style={{ marginTop: 0, marginBottom: "10px", fontSize: "14px" }}>
            Recent Interactions:
          </h3>
          {interactions.length === 0 ? (
            <p style={{ color: "#666", fontSize: "12px" }}>
              No interactions recorded yet.
            </p>
          ) : (
            <div style={{ fontSize: "12px" }}>
              {interactions.slice(0, 50).map((event, index) => (
                <div
                  key={event.id}
                  style={{
                    padding: "8px",
                    marginBottom: "5px",
                    backgroundColor: index % 2 === 0 ? "#f8f9fa" : "white",
                    borderRadius: "3px",
                    borderLeft: `3px solid ${
                      event.type === "page-load"
                        ? "#4CAF50"
                        : event.type === "click"
                        ? "#2196F3"
                        : event.type === "type"
                        ? "#FF9800"
                        : "#666"
                    }`,
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      marginBottom: "4px",
                    }}
                  >
                    <span style={{ fontWeight: "bold" }}>
                      {getEventIcon(event.type)} {event.type}
                      {event.tabId && (
                        <span
                          style={{
                            fontSize: "10px",
                            marginLeft: "5px",
                            padding: "2px 4px",
                            backgroundColor: "#e3f2fd",
                            borderRadius: "3px",
                            color: "#1976d2",
                          }}
                        >
                          Tab {event.tabId}
                        </span>
                      )}
                    </span>
                    <span style={{ color: "#666" }}>
                      {formatTimestamp(event.timestamp)}
                    </span>
                  </div>

                  {event.url && (
                    <div
                      style={{
                        color: "#666",
                        marginBottom: "2px",
                        wordBreak: "break-all",
                      }}
                    >
                      📍 {event.url.substring(0, 50)}...
                    </div>
                  )}

                  {event.title && (
                    <div style={{ color: "#666", marginBottom: "2px" }}>
                      📝 {event.title.substring(0, 40)}...
                    </div>
                  )}

                  {event.windowId && (
                    <div
                      style={{
                        color: "#666",
                        marginBottom: "2px",
                        fontSize: "11px",
                      }}
                    >
                      🪟 Window ID: {event.windowId}
                    </div>
                  )}

                  {event.payload && (
                    <details style={{ marginTop: "4px" }}>
                      <summary style={{ cursor: "pointer", color: "#007bff" }}>
                        View payload (ID: {event.id?.substring(0, 8)}...)
                      </summary>
                      <pre
                        style={{
                          fontSize: "10px",
                          backgroundColor: "#f5f5f5",
                          padding: "5px",
                          borderRadius: "3px",
                          overflow: "auto",
                          maxHeight: "100px",
                          marginTop: "4px",
                        }}
                      >
                        {JSON.stringify(
                          {
                            ...event.payload,
                            eventId: event.id,
                            tabId: event.tabId,
                            windowId: event.windowId,
                          },
                          null,
                          2
                        )}
                      </pre>
                    </details>
                  )}
                </div>
              ))}
              {interactions.length > 50 && (
                <div
                  style={{
                    textAlign: "center",
                    color: "#666",
                    marginTop: "10px",
                    fontStyle: "italic",
                  }}
                >
                  Showing first 50 of {interactions.length} interactions
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
