from aiohttp import web
from ovos_stt_http_server import AsyncContext, handle_raw_audio
from ovos_plugin_manager.stt import load_stt_plugin

routes = web.RouteTableDef()

models = {}


@routes.post('/stt')
async def handle_stt(request):

    lang = request.query.get('lang', 'en-us').lower()
    model = models.get(lang) or models.get(lang.split("-")[0])

    ctx = AsyncContext(model)

    await ctx.start_stream()

    await handle_raw_audio(request, ctx, 2)

    text = await ctx.stop_stream()

    return web.Response(text=text)


def main():
    global models
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", help="stt plugin to be used")
    parser.add_argument("--port", help="port number", default=8080)
    parser.add_argument("--host", help="host", default="0.0.0.0")
    args = parser.parse_args()

    engine = load_stt_plugin(args.engine)

    # TODO one model per language cli args support
    models["en"] = engine

    app = web.Application()
    app.add_routes(routes)

    web.run_app(app, host=args.host, port=args.port)


if __name__ == '__main__':
    main()
