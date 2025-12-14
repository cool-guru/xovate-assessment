import { FormEvent, useMemo, useState } from "react";
import "./App.css";

type ValidationStatus = "pass" | "fail";

type ValidationError = {
  row_index: number | null;
  id: number | null;
  column: string;
  error_message: string;
};

type ValidationResponse = {
  status: ValidationStatus;
  errors: ValidationError[];
};

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

const normalizeBaseUrl = (url: string): string => url.replace(/\/$/, "");

function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [result, setResult] = useState<ValidationResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [requestError, setRequestError] = useState<string | null>(null);

  const errorCount = result?.errors.length ?? 0;
  const statusText = useMemo(() => {
    if (!result) return "–";
    return result.status === "pass" ? "Looks good" : `${errorCount} issue${errorCount === 1 ? "" : "s"}`;
  }, [result, errorCount]);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.item(0) ?? null;
    setSelectedFile(file);
    setResult(null);
    setRequestError(null);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedFile) {
      setRequestError("Please choose a CSV file before submitting.");
      return;
    }

    setIsSubmitting(true);
    setRequestError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile, selectedFile.name);
      const response = await fetch(`${normalizeBaseUrl(API_BASE_URL)}/validate`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        let errorMessage = `Request failed with status ${response.status}`;
        try {
          const payload = await response.json();
          if (payload?.detail) {
            errorMessage = typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail);
          }
        } catch (parseError) {
          // ignore JSON parse errors and surface the default message
        }
        throw new Error(errorMessage);
      }

      const payload = (await response.json()) as ValidationResponse;
      setResult(payload);
    } catch (error) {
      if (error instanceof Error) {
        setRequestError(error.message);
      } else {
        setRequestError("Unexpected error while uploading file.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="page">
      <main className="panel">
        <header>
          <p className="eyebrow">Xovate Data Validation Engine</p>
          <h1>Upload a CSV and see exactly what breaks</h1>
        </header>

        <section className="card">
          <h2>1. Choose a CSV</h2>
          <form onSubmit={handleSubmit} className="upload-form">
            <label htmlFor="csv-upload" className="file-picker">
              <span>{selectedFile ? selectedFile.name : "Select or drop a file"}</span>
              <input
                id="csv-upload"
                type="file"
                name="file"
                accept=".csv,text/csv"
                onChange={handleFileChange}
                disabled={isSubmitting}
              />
            </label>
            <button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Validating…" : "Validate"}
            </button>
          </form>
          <p className="hint">Use the included sample CSVs in the repo to quickly check pass/fail behavior.</p>
        </section>

        <section className="card">
          <h2>2. Results</h2>
          <div className="result-summary" data-status={result?.status ?? "idle"}>
            <span className="status-label">Status:</span>
            <strong>{result ? result.status.toUpperCase() : "Pending"}</strong>
            <span className="status-text">{statusText}</span>
          </div>

          {requestError && <p className="error-banner">{requestError}</p>}

          {result && errorCount === 0 && <p className="success-banner">No validation errors</p>}

          {result && errorCount > 0 && (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Row #</th>
                    <th>ID</th>
                    <th>Column</th>
                    <th>Error</th>
                  </tr>
                </thead>
                <tbody>
                  {result.errors.map((error, index) => (
                    <tr key={`${error.row_index}-${error.column}-${index}`}>
                      <td>{error.row_index ?? "–"}</td>
                      <td>{error.id ?? "–"}</td>
                      <td>{error.column}</td>
                      <td>{error.error_message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
