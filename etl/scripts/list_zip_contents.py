import zipfile, os, sys
root = sys.argv[1] if len(sys.argv)>1 else os.path.join(os.path.dirname(__file__), '..','data','raw','demonstracoes_contabeis','2025')
root = os.path.abspath(root)
for fname in sorted(os.listdir(root)):
    path = os.path.join(root,fname)
    if zipfile.is_zipfile(path):
        print('---', fname)
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                print('   ', info.filename, info.file_size)
    else:
        print('SKIP', fname)
