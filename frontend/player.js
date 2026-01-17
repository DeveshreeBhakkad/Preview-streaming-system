const video = document.getElementById("videoPlayer");

const mediaSource = new MediaSource();
video.src = URL.createObjectURL(mediaSource);

mediaSource.addEventListener("sourceopen", async () => {
    const mimeCodec = 'video/mp4; codecs="avc1.42E01E, mp4a.40.2"';

    if (!MediaSource.isTypeSupported(mimeCodec)) {
        console.error("Codec not supported:", mimeCodec);
        return;
    }

    const sourceBuffer = mediaSource.addSourceBuffer(mimeCodec);

    try {
        const response = await fetch("http://127.0.0.1:8000/video-controlled");
        const reader = response.body.getReader();

        while (true) {
            const { value, done } = await reader.read();
            if (done) {
                mediaSource.endOfStream();
                break;
            }

            await waitForSourceBuffer(sourceBuffer);
            sourceBuffer.appendBuffer(value);
        }
    } catch (err) {
        console.error("Streaming error:", err);
    }
});

function waitForSourceBuffer(sourceBuffer) {
    return new Promise(resolve => {
        if (!sourceBuffer.updating) {
            resolve();
        } else {
            sourceBuffer.addEventListener("updateend", resolve, { once: true });
        }
    });
}
