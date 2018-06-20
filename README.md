# SIWeightEditor
SoftimageにあったWeightEditorをリスペクトして作成したMaya用SkinWeight編集プラグインです。  
![image](https://user-images.githubusercontent.com/28256498/41656611-8d04f67a-74cb-11e8-856d-c365d2957ed6.png)

## インストール

Clone or download > Download ZIP もしくは  
release > Source code (zip) からZIPファイルをダウンロードしてください。  

解凍したSiWeightEditorフォルダを C:\Program Files\Autodesk\ApplicationPlugins へコピーしてください。  
ディレクトリ構成などは変更せず解凍フォルダごとそのまま設置します。  

![image](https://user-images.githubusercontent.com/28256498/41656276-639ab2d0-74ca-11e8-8be2-3c26f8a17927.png)

MayaをCドライブ以外にインストールしている場合でも  
C:\Program Files\Autodesk\ApplicationPlugins  
に置く必要があるようです。  

ApplicationPluginsフォルダが存在しない場合は作成してください。  

動作確認はMaya2015～2018で行っています。  

## 主な機能

### 基本UI表示
![image](https://user-images.githubusercontent.com/28256498/41656766-14a74cae-74cc-11e8-8226-e19d64a98ae2.png)
Show → 選択したテーブルセルに表示をフォーカスする。  
Show All → オブジェクトのウェイトを全表示する  
Focus　→ コンポーネント選択をセル表示に反映する  
Filter → 表示されているインフルエンスのうちウェイト合計が0のものを非表示にする  
Highlite → セル選択された頂点をビューポート上でハイライトする  
![siweighteditor1](https://user-images.githubusercontent.com/28256498/41657246-b371c3e0-74cd-11e8-8dbd-5a5b3828902c.gif)

### ジョイント設定
![image](https://user-images.githubusercontent.com/28256498/41657474-6d59d6d0-74ce-11e8-964c-095097aeb6a3.png)



