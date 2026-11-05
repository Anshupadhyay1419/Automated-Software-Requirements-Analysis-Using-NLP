import { useCallback, useEffect, useState } from "react";

// Loads data for a page and tracks its loading and error state.
export function useLoad(loader, dependencies = []) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    try {
      setData(await loader());
      setError("");
    } catch (problem) {
      setError(problem.message);
    } finally {
      setLoading(false);
    }
  }, dependencies); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    setLoading(true);
    reload();
  }, [reload]);

  return { data, setData, error, setError, loading, reload };
}
