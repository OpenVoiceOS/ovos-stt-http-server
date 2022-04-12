from asgiref.sync import sync_to_async


class AsyncContext:
    def __init__(self, model):
        self.model = model
        self.text = None
        self.buffer = []

    async def start_stream(self):
        if self.model.can_stream:
            await sync_to_async(self.model.stream_start)()

    async def stream_data(self, frames):
        self.buffer.append(frames)
        if self.model.can_stream:
            await sync_to_async(self.model.stream_data)(frames)

    async def stop_stream(self):
        if self.model.can_stream:
            text = await sync_to_async(self.model.stream_stop)()
        else:
            # TODO AudioData object from bytes as expected by plugins
            text = await sync_to_async(self.model.execute)(self.buffer)
        self.buffer = []
        return text


async def handle_raw_audio(request, ctx, sample_width):
    while True:
        frames = await request.content.read(sample_width * 512)
        if not frames:
            break
        await ctx.stream_data(frames)
