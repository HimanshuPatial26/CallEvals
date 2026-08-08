import { render, screen } from "@testing-library/react";
import App from "./App";

jest.mock("./api/client", () => ({
  listCalls: jest.fn().mockResolvedValue([]),
}));

test("renders the CallEvals header", () => {
  render(<App />);
  expect(screen.getByText("CallEvals")).toBeInTheDocument();
});
