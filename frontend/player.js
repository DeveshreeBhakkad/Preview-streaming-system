const video = document.getElementById("videoPlayer");

// Create MediaSource
const mediaSource = new MediaSource();
video.src = URL.createObjectURL(mediaSource);

mediaSource.addEventListener("sourceopen", () => {
    const mimeCodec = 'video/mp4; codecs="avc1.42E01E, mp4a.40.2"';

    if (!MediaSource.isTypeSupported(mimeCodec)) {
        console.error("Unsupported codec");
        return;
    }

    const sourceBuffer = mediaSource.addSourceBuffer(mimeCodec);

    fetchAndAppendChunks(sourceBuffer);
});

async function fetchAndAppendChunks(sourceBuffer) {
    const response = await fetch("http://127.0.0.1:8000/video-controlled");
    const reader = response.body.getReader();

    while (true) {
        const { value, done } = await reader.read();
        if (done) {
            mediaSource.endOfStream();
            break;
        }

        // Wait if SourceBuffer is busy
        if (sourceBuffer.updating) {
            await waitForUpdateEnd(sourceBuffer);
        }

        sourceBuffer.appendBuffer(value);
    }
}

function waitForUpdateEnd(sourceBuffer) {
    return new Promise(resolve => {
        sourceBuffer.addEventListener("updateend", resolve, { once: true });
    });
}
