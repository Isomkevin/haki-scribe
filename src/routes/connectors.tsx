import { createFileRoute, redirect } from "@tanstack/react-router";

export const Route = createFileRoute("/connectors")({
  beforeLoad: () => {
    throw redirect({ to: "/settings" });
  },
});
