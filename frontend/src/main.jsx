import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import "./index.css";
import Layout from "./components/Layout";
import ProjectLayout from "./components/ProjectLayout";
import ProjectsPage from "./pages/ProjectsPage";
import OverviewPage from "./pages/OverviewPage";
import SourcePage from "./pages/SourcePage";
import RequirementsPage from "./pages/RequirementsPage";
import DuplicatesPage from "./pages/DuplicatesPage";
import QualityPage from "./pages/QualityPage";
import StoriesPage from "./pages/StoriesPage";
import ExportPage from "./pages/ExportPage";
import ModelPage from "./pages/ModelPage";
import SettingsPage from "./pages/SettingsPage";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<ProjectsPage />} />
          <Route path="model" element={<ModelPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="projects/:projectId" element={<ProjectLayout />}>
            <Route index element={<OverviewPage />} />
            <Route path="source" element={<SourcePage />} />
            <Route path="requirements" element={<RequirementsPage />} />
            <Route path="duplicates" element={<DuplicatesPage />} />
            <Route path="quality" element={<QualityPage />} />
            <Route path="stories" element={<StoriesPage />} />
            <Route path="export" element={<ExportPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
