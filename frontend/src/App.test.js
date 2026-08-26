import { render, screen } from "@testing-library/react";
import App from "./App";
import * as api from "./api/client";

jest.mock("./api/client");

const DEFAULT_SETTINGS = {
  weights: { discovery: 25, objection: 25, listening: 20, nextstep: 20, compliance: 10 },
  flags: {
    monologue: true,
    no_discovery_question: true,
    no_dated_next_step: true,
    missing_disclosure: true,
    discount_offered_first: false,
  },
  objection_tags: ["price", "timing", "competitor"],
  surface_threshold: 70,
  autoflag_threshold: 88,
  digest: "Daily",
  retention_days: 180,
  rep_private_mode: true,
  composite_score_enabled: false,
};

// CRA's default jest config sets resetMocks: true, which strips any implementation
// set at jest.mock() factory time before each test runs — so implementations have
// to be (re-)applied here, not in the mock factory above.
beforeEach(() => {
  api.listCalls.mockResolvedValue([]);
  api.listAgents.mockResolvedValue([]);
  api.listLeads.mockResolvedValue([]);
  api.getSettings.mockResolvedValue(DEFAULT_SETTINGS);
});

test("renders the CallEvals header", () => {
  render(<App />);
  expect(screen.getByText("CallEvals")).toBeInTheDocument();
});
