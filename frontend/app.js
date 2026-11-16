import { AudioCapture } from "./audio/audio_capture.js";


const startButton = document.getElementById("startButton");
const stopButton = document.getElementById("stopButton");

const statusElement = document.getElementById("status");
const statsElement = document.getElementById("stats");

const partialElement = document.getElementById("partialTranscript");
const finalElement = document.getElementById("finalTranscript");


let websocket = null;
let audioCapture = null;
let sessionReady = false;


function setStatus(message) {

    statusElement.textContent = message;
}


function updateStats(data) {

    statsElement.textContent =
        `Audio: ${data.duration_seconds}s | ` +
        `Chunks: ${data.chunks_received ?? 0} | ` +
        `Queue: ${data.queue_size ?? 0}`;
}


function waitForEvent(eventType, timeout = 10000) {

    return new Promise((resolve, reject) => {

        const timer = setTimeout(() => {

            cleanup();

            reject(
                new Error(`Timeout waiting for ${eventType}`)
            );

        }, timeout);

        function cleanup() {

            clearTimeout(timer);

            websocket.removeEventListener(
                "message",
                handler
            );
        }

        function handler(event) {

            const message = JSON.parse(event.data);

            if (message.type === "session.error") {

                cleanup();

                reject(
                    new Error(message.data.message)
                );

                return;
            }

            if (message.type === eventType) {

                cleanup();

                resolve(message.data);
            }
        }

        websocket.addEventListener(
            "message",
            handler
        );
    });
}


function connectWebSocket() {

    return new Promise((resolve, reject) => {

        const protocol =
            location.protocol === "https:"
                ? "wss:"
                : "ws:";

        websocket = new WebSocket(
            `${protocol}//${location.host}/ws/audio`
        );

        websocket.binaryType = "arraybuffer";

        websocket.onopen = resolve;

        websocket.onerror = () => {

            reject(
                new Error("WebSocket connection failed.")
            );
        };

        websocket.onmessage = (event) => {

            const message = JSON.parse(event.data);
            const data = message.data;

            switch (message.type) {

                case "session.ready":

                    sessionReady = true;

                    setStatus("Recording");

                    break;

                case "audio.stats":

                    updateStats(data);

                    break;

                case "asr.status":

                    if (data.state === "processing") {
                        setStatus("Transcribing...");
                    }

                    if (data.state === "queued") {
                        setStatus("Recording / ASR queued");
                    }

                    if (data.state === "queue_full") {
                        setStatus("ASR is falling behind");
                    }

                    break;

                case "asr.partial":

                    partialElement.textContent =
                        data.text || "";

                    break;

                case "asr.final":

                    finalElement.textContent =
                        data.text || "(No speech detected)";

                    partialElement.textContent = "";

                    setStatus("Final transcription received");

                    break;

                case "asr.error":

                    console.error("ASR error:", data);

                    setStatus(
                        `ASR error: ${data.message}`
                    );

                    break;

                case "session.error":

                    setStatus(
                        `Session error: ${data.message}`
                    );

                    break;

                case "session.closed":

                    sessionReady = false;

                    startButton.disabled = false;
                    stopButton.disabled = true;

                    setStatus("Session closed");

                    break;
            }
        };

        websocket.onclose = () => {

            sessionReady = false;

            startButton.disabled = false;
            stopButton.disabled = true;

            setStatus("Disconnected");
        };
    });
}


async function ensureConnection() {

    if (
        websocket &&
        websocket.readyState === WebSocket.OPEN
    ) {
        return;
    }

    await connectWebSocket();
}


async function startRecording() {

    startButton.disabled = true;

    try {

        setStatus("Connecting...");

        await ensureConnection();

        partialElement.textContent = "";
        finalElement.textContent = "";

        audioCapture = new AudioCapture((audioChunk) => {

            if (
                websocket &&
                websocket.readyState === WebSocket.OPEN &&
                sessionReady
            ) {

                websocket.send(audioChunk.buffer);
            }
        });

        // Initialize microphone but do not transmit audio.
        const config = await audioCapture.start({
            paused: true
        });

        // Register the waiter BEFORE sending the message.
        const readyPromise = waitForEvent(
            "session.ready"
        );

        websocket.send(JSON.stringify({

            type: "session.start",

            data: {
                sample_rate: config.sampleRate,
                channels: 1,
                encoding: "float32le"
            }

        }));

        await readyPromise;

        // Only now allow the worklet to transmit audio.
        audioCapture.resume();

        stopButton.disabled = false;

    } catch (error) {

        console.error(error);

        setStatus(error.message);

        if (audioCapture) {

            await audioCapture.stop();

            audioCapture = null;
        }

        sessionReady = false;

        if (
            websocket &&
            websocket.readyState === WebSocket.OPEN
        ) {
            websocket.close();
        }

        websocket = null;

        startButton.disabled = false;
        stopButton.disabled = true;
    }
}


async function stopRecording() {

    stopButton.disabled = true;

    try {

        if (audioCapture) {

            // Flush final samples before audio.end.
            await audioCapture.stop();

            audioCapture = null;
        }

        if (
            websocket &&
            websocket.readyState === WebSocket.OPEN
        ) {

            const closedPromise = waitForEvent(
                "session.closed",
                120000
            );

            websocket.send(JSON.stringify({

                type: "audio.end",
                data: {}

            }));

            setStatus("Waiting for final transcription...");

            await closedPromise;
        }

    } catch (error) {

        console.error(error);

        setStatus(error.message);

    } finally {

        sessionReady = false;

        startButton.disabled = false;
        stopButton.disabled = true;
    }
}


startButton.addEventListener(
    "click",
    startRecording
);

stopButton.addEventListener(
    "click",
    stopRecording
);