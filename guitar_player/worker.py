import sys
from pathlib import Path
import traceback
from .storage import atomic_json, read_json


def main():
    kind, path = sys.argv[1], Path(sys.argv[2])
    request = read_json(path/'request.json')
    def progress(message):
        atomic_json(path/'progress.json', {'message': message})
    try:
        if kind == 'transcribe':
            from .transcription import transcribe
            result = transcribe(request['source'], path, request['model'], progress)
            atomic_json(path/'transcription.json', result.to_dict())
            atomic_json(path/'result.json', {'transcription': str(path/'transcription.json')})
        elif kind == 'preview':
            from .preview import render_request
            result = render_request(request, path, progress)
            atomic_json(path/'result.json', result)
        else:
            raise ValueError('未知作业类型')
        progress('处理完成')
        return 0
    except Exception as exc:
        progress(str(exc))
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
