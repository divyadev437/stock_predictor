document.addEventListener("DOMContentLoaded", function() {

    // --- Initialize Date Picker for Single Future Date ---
    const today = new Date();
    const predictionDatePicker = flatpickr("#prediction-date", {
        dateFormat: "Y-m-d",
        minDate: today.fp_incr(1), // Allow selection from tomorrow onwards
        // defaultDate: today.fp_incr(7) // Optionally default to 7 days ahead
    });

    // --- Get DOM Elements ---
    const form = document.getElementById("prediction-form");
    const predictButton = document.getElementById("predict-button");
    const spinner = predictButton.querySelector(".spinner-border");

    const alertBox = document.getElementById("alert-box");
    const alertMsg = alertBox.querySelector(".alert");

    const resultsSection = document.getElementById("results-section");
    const chartSection = document.getElementById("chart-section");

    // Chart Containers
    const fullHistoricalChartDiv = document.getElementById("full-historical-chart");
    const last30DaysChartDiv = document.getElementById("last-30-days-chart");
    const predictedTrendChartDiv = document.getElementById("predicted-trend-chart");


    // Result display elements
    const resultStockName = document.getElementById("result-stock-name");
    const resultPredictedDate = document.getElementById("result-predicted-date");
    const resultModel = document.getElementById("result-model");
    const resultConfidence = document.getElementById("result-confidence");
    const resultPredictedPrice = document.getElementById("result-predicted-price");


    // --- Form Submit Handler ---
    form.addEventListener("submit", function(event) {
        event.preventDefault(); // Stop form submission

        // 1. Get Form Data
        const stock = document.getElementById("stock-select").value;
        const model = document.getElementById("model-select").value;
        const predictionDates = predictionDatePicker.selectedDates;

        // 2. Validate Prediction Date
        if (predictionDates.length === 0) {
            showAlert("Please select a future prediction date.");
            return;
        }
        const predictionDate = formatDate(predictionDates[0]); // Format YYYY-MM-DD

        // 3. Prepare for Fetch
        showLoading(true);
        hideAlert();
        // Hide previous results immediately
        resultsSection.classList.add("d-none");
        chartSection.classList.add("d-none");

        const requestData = {
            stock: stock,
            model: model,
            prediction_date: predictionDate
        };

        // 4. Send Fetch Request to Flask Backend
        fetch("/predict", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(requestData)
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.error || `Server error: ${response.status}`); });
            }
            return response.json();
        })
        .then(data => {
            // 5. Handle Success
            showLoading(false);
            if (data.error) {
                showAlert(data.error);
            } else {
                // Success! Update UI and plot data
                updateResults(data);
                plotFullHistoricalTrend(data.full_historical_data, data.stock_name);
                plotLast30DaysTrend(data.historical_30_data, data.predicted_date, data.predicted_price, data.stock_name);
                plotPredictedTrend(data.predicted_trend_data, data.stock_name);

                resultsSection.classList.remove("d-none");
                chartSection.classList.remove("d-none");
            }
        })
        .catch(error => {
            // 6. Handle Fetch/Network Errors
            console.error("Fetch Error:", error);
            showLoading(false);
            showAlert(error.message || "An unknown error occurred during prediction.");
        });
    });

    // --- Plotly Layout (Adjusted for White/Blue Theme) ---
    const plotLayout = {
        plot_bgcolor: 'white', // White background for the plot area itself
        paper_bgcolor: 'white', // White background for the whole chart area
        autosize: true,
        font: {
            family: 'Roboto, sans-serif', // Use a common sans-serif font
            color: '#333333' // Darker text for light theme
        },
        xaxis: {
            autorange: true,
            gridcolor: '#e0e0e0', // Light gray grid lines
            linecolor: '#cccccc', // Axis line color
            tickfont: { color: '#333333' },
            titlefont: { color: '#333333' },
            showgrid: true,
            zeroline: false,
            type: 'date'
        },
        yaxis: {
            autorange: true,
            gridcolor: '#e0e0e0', // Light gray grid lines
            linecolor: '#cccccc', // Axis line color
            tickfont: { color: '#333333' },
            titlefont: { color: '#333333' },
            showgrid: true,
            zeroline: false
        },
        legend: {
            x: 0.01, y: 0.99,
            font: { color: '#333333' },
            bgcolor: 'rgba(255, 255, 255, 0.7)', // Semi-transparent white background for legend
            bordercolor: '#cccccc',
            borderwidth: 1
        },
        title: {
             font: { color: '#333333' }
         },
        dragmode: 'pan'
    };

    // --- Plotting Functions for each chart ---

    function plotFullHistoricalTrend(data, stockName) {
        const trace = {
            x: data.x,
            y: data.y,
            type: 'scatter',
            mode: 'lines',
            name: 'Historical Close Price',
            line: { color: '#0d6efd' } // Primary blue
        };

        const layout = {
            ...plotLayout,
            title: `Full Historical Closing Price Trend for ${stockName}`
        };

        const config = { responsive: true };
        Plotly.newPlot(fullHistoricalChartDiv, [trace], layout, config);
    }

    function plotLast30DaysTrend(data, predictedDate, predictedPrice, stockName) {
        // Find the index where the predictedDate would fit in the x-axis
        const historicalX = data.x;
        const historicalY = data.y;

        const combinedX = [...historicalX, predictedDate];
        const combinedY = [...historicalY, predictedPrice];

        // Sort by date to ensure line connects correctly
        const sortedData = combinedX.map((date, i) => ({ date: new Date(date), price: combinedY[i] }))
                                    .sort((a, b) => a.date - b.date);

        const traceHistorical = {
            x: sortedData.map(d => d.date.toISOString().split('T')[0]),
            y: sortedData.map(d => d.price),
            type: 'scatter',
            mode: 'lines',
            name: 'Historical & Predicted',
            line: { color: '#0d6efd' } // Primary blue
        };

        const tracePredictionPoint = {
            x: [predictedDate],
            y: [predictedPrice],
            type: 'scatter',
            mode: 'markers',
            marker: { size: 10, color: 'red', symbol: 'circle' },
            name: 'Predicted Price',
            hoverinfo: 'x+y+name' // show date, price and name on hover
        };

        const layout = {
            ...plotLayout,
            title: `Last 30 Days Price Trend for ${stockName} with ${predictedDate} Prediction`
        };

        const config = { responsive: true };
        Plotly.newPlot(last30DaysChartDiv, [traceHistorical, tracePredictionPoint], layout, config);
    }

    function plotPredictedTrend(data, stockName) {
        const trace = {
            x: data.x,
            y: data.y,
            type: 'scatter',
            mode: 'lines+markers', // Lines and markers for future trend
            name: 'Predicted Trend',
            line: { color: '#dc3545' }, // Red for prediction
            marker: { size: 6 }
        };

        const layout = {
            ...plotLayout,
            title: `Predicted Price Trend for ${stockName} (Next 15 Days)`
        };

        const config = { responsive: true };
        Plotly.newPlot(predictedTrendChartDiv, [trace], layout, config);
    }


    // --- UI Helper Functions ---

    function updateResults(data) {
        resultStockName.textContent = data.stock_name;
        resultPredictedDate.textContent = data.predicted_date;
        resultModel.textContent = data.prediction_model;
        resultConfidence.textContent = data.confidence;
        resultPredictedPrice.textContent = `₹ ${data.predicted_price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }

    function showLoading(isLoading) {
        spinner.classList.toggle("d-none", !isLoading);
        predictButton.disabled = isLoading;
        predictButton.innerHTML = isLoading
            ? `<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Predicting...`
            : `Predict Stock`;
    }

    function showAlert(message) {
        alertMsg.textContent = message;
        alertBox.classList.remove("d-none");
    }

    function hideAlert() {
        alertBox.classList.add("d-none");
    }

    function formatDate(date) {
        return date.toISOString().split('T')[0];
    }

});