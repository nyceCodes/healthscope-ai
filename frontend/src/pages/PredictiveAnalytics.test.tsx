import { AxiosHeaders, type AxiosResponse } from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import * as healthApi from "../services/healthApi";
import PredictiveAnalytics from "./PredictiveAnalytics";

vi.mock("../services/healthApi", () => ({
    getPredictionHistory: vi.fn(),
    predictLifeExpectancy: vi.fn(),
}));

const getHistory = vi.mocked(healthApi.getPredictionHistory);
const predict = vi.mocked(healthApi.predictLifeExpectancy);

function axiosResponse<T>(data: T): AxiosResponse<T> {
    const headers = new AxiosHeaders();
    return {
        data,
        status: 200,
        statusText: "OK",
        headers,
        config: { headers },
    };
}

describe("PredictiveAnalytics", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        getHistory.mockResolvedValue(axiosResponse([]));
    });

    afterEach(() => {
        cleanup();
    });

    it("validates inputs before sending a prediction request", async () => {
        render(<PredictiveAnalytics />);
        await screen.findByText("No saved predictions yet.");

        fireEvent.change(screen.getByLabelText(/Adult mortality/), {
            target: { value: "-1" },
        });
        fireEvent.click(screen.getByRole("button", { name: "Estimate life expectancy" }));

        expect((await screen.findByRole("alert")).textContent).toContain(
            "Adult mortality must be a finite number",
        );
        expect(predict).not.toHaveBeenCalled();
    });

    it("shows a successful prediction even when refreshing history fails", async () => {
        getHistory
            .mockResolvedValueOnce(axiosResponse([]))
            .mockRejectedValueOnce(new Error("History unavailable"));
        predict.mockResolvedValue({
            data: { predicted_life_expectancy: 72.4 },
            status: 200,
            statusText: "OK",
            headers: new AxiosHeaders(),
            config: { headers: new AxiosHeaders() },
        });

        render(<PredictiveAnalytics />);
        await screen.findByText("No saved predictions yet.");
        fireEvent.click(screen.getByRole("button", { name: "Estimate life expectancy" }));

        expect(await screen.findByText("72.4 years")).not.toBeNull();
        await waitFor(() => {
            expect(screen.getByRole("alert").textContent).toContain("History unavailable");
        });
    });

    it("reports an unexpected prediction response instead of rendering it", async () => {
        predict.mockResolvedValue({
            data: { predicted_life_expectancy: "not a number" },
            status: 200,
            statusText: "OK",
            headers: new AxiosHeaders(),
            config: { headers: new AxiosHeaders() },
        } as unknown as Awaited<ReturnType<typeof healthApi.predictLifeExpectancy>>);

        render(<PredictiveAnalytics />);
        fireEvent.click(screen.getByRole("button", { name: "Estimate life expectancy" }));

        expect((await screen.findByRole("alert")).textContent).toContain(
            "The prediction service returned an invalid result.",
        );
        expect(screen.queryByText("72.4 years")).toBeNull();
    });
});
