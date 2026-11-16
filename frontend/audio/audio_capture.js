export class AudioCapture {

    constructor(onAudioChunk) {

        this.onAudioChunk = onAudioChunk;

        this.audioContext = null;
        this.mediaStream = null;
        this.source = null;
        this.worklet = null;

        this.isRunning = false;
    }

    async start({ paused = true } = {}) {

        if (this.isRunning) {
            return;
        }

        try {

            this.mediaStream =
                await navigator.mediaDevices.getUserMedia({

                    audio: {
                        channelCount: 1,
                        echoCancellation: false,
                        noiseSuppression: false,
                        autoGainControl: false
                    }

                });

            this.audioContext = new AudioContext();

            await this.audioContext.audioWorklet.addModule(
                "/audio/pcm-processor.js"
            );

            this.source =
                this.audioContext.createMediaStreamSource(
                    this.mediaStream
                );

            this.worklet = new AudioWorkletNode(
                this.audioContext,
                "pcm-processor"
            );

            this.worklet.port.onmessage = (event) => {

                if (event.data.type === "audio") {

                    this.onAudioChunk?.(
                        event.data.audio
                    );
                }

                if (event.data.type === "flushed") {

                    this.flushResolve?.();

                    this.flushResolve = null;
                }
            };

            this.source.connect(this.worklet);

            // The worklet produces silence at its output.
            this.worklet.connect(
                this.audioContext.destination
            );

            await this.audioContext.resume();

            this.isRunning = true;

            if (!paused) {
                this.resume();
            }

            return {
                sampleRate: this.audioContext.sampleRate,
                channels: 1
            };

        } catch (error) {

            await this.cleanup();

            throw error;
        }
    }

    resume() {

        if (!this.isRunning) {
            throw new Error("Audio capture is not initialized.");
        }

        this.worklet.port.postMessage({
            command: "start"
        });
    }

    async stop() {

        if (!this.isRunning) {
            return;
        }

        // Request delivery of the incomplete final chunk.
        const flushPromise = new Promise((resolve) => {

            this.flushResolve = resolve;

        });

        this.worklet.port.postMessage({
            command: "flush"
        });

        // Avoid waiting indefinitely if the worklet fails.
        await Promise.race([

            flushPromise,

            new Promise(resolve =>
                setTimeout(resolve, 2000)
            )

        ]);

        this.isRunning = false;

        await this.cleanup();
    }

    async cleanup() {

        if (this.worklet) {

            this.worklet.port.onmessage = null;

            this.worklet.disconnect();
            this.worklet = null;
        }

        if (this.source) {

            this.source.disconnect();
            this.source = null;
        }

        if (this.mediaStream) {

            this.mediaStream.getTracks().forEach(
                track => track.stop()
            );

            this.mediaStream = null;
        }

        if (this.audioContext) {

            await this.audioContext.close();

            this.audioContext = null;
        }

        this.isRunning = false;
    }
}