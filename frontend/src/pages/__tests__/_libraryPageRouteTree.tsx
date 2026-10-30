/**
 * A small route tree for tests that must arrive at LibraryPage by navigating,
 * since it reads router state only when it mounts. Leading-underscore filename
 * = not a test file.
 */
import type { ReactNode } from "react";
import { Route, Routes } from "react-router";

export function RouteTree({
  launcher,
  page,
}: {
  launcher: ReactNode;
  page: ReactNode;
}) {
  return (
    <>
      {launcher}
      <Routes>
        <Route path="/guided" element={page} />
        <Route path="*" element={null} />
      </Routes>
    </>
  );
}
