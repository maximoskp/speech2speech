class PCMProcessor extends AudioWorkletProcessor {

    constructor() {
        super();

        this.chunkSize = Math.round(sampleRate * 0.1);

        this.buffer = new Float32Array(this.chunkSize);
        this.bufferPosition = 0;

        this.active = false;

        this.port.onmessage = (event) => {

            const command = event.data.command;

            if (command === "start") {
                this.active = true;
            }

            if (command === "flush") {
                
                this.active = false;

                this.flush();

                this.port.postMessage({
                    type: "flushed"
                });
            }
        };
    }

    flush() {

        if (this.bufferPosition > 0) {

            const chunk = this.buffer.slice(
                0,
                this.bufferPosition
            );

            this.port.postMessage(
                {
                    type: "audio",
                    audio: chunk
                },
                [chunk.buffer]
            );
        }

        this.buffer = new Float32Array(this.chunkSize);
        this.bufferPosition = 0;
    }

    process(inputs, outputs) {

        const input = inputs[0];

        if (!this.active || !input || !input[0]) {
            return true;
        }

        const channel = input[0];

        for (let i = 0; i < channel.length; i++) {

            this.buffer[this.bufferPosition++] = channel[i];

            if (this.bufferPosition >= this.chunkSize) {

                this.flush();
            }
        }

        return true;
    }
}

registerProcessor(
    "pcm-processor",
    PCMProcessor
);