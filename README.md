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

### 基本UI表示1
![image](https://user-images.githubusercontent.com/28256498/41656766-14a74cae-74cc-11e8-8226-e19d64a98ae2.png)

Show → 選択したテーブルセルに表示をフォーカスする。  
Show All → オブジェクトのウェイトを全表示する  
Focus　→ コンポーネント選択をセル表示に反映する  
Filter → 表示されているインフルエンスのうちウェイト合計が0のものを非表示にする  
Highlite → セル選択された頂点をビューポート上でハイライトする  
![siweighteditor1](https://user-images.githubusercontent.com/28256498/41657246-b371c3e0-74cd-11e8-8dbd-5a5b3828902c.gif)

### 基本UI表示2
![image](https://user-images.githubusercontent.com/28256498/41657474-6d59d6d0-74ce-11e8-964c-095097aeb6a3.png)

鍵マーク　→ メッシュ選択変更のUIへの反映をロックします。一時的にウェイトエディタ表示の更新を止めたい場合に  
サイクルマーク　→ 現在の選択をUIに反映します。鍵マークでロックがかかっていても強制的に反映  
Cマーク　→ 表示のクリア  
⇄マーク　→ セル上の選択頂点を実際に選択し、UI表示も絞り込みます。  
0-1　→ ウェイトを0.0～1.0で表示します（Maya仕様）  
0-100　→ ウェイトを0.0～100.0で表示します（SI仕様）  
![siweighteditor2](https://user-images.githubusercontent.com/28256498/41657833-95a15ab8-74cf-11e8-883c-27eb48edcd21.gif)

### 不正な頂点ウェイトの絞り込み
![image](https://user-images.githubusercontent.com/28256498/41658281-dcc32786-74d0-11e8-8d9e-b0eccb5785b3.png)

本エディタでは不正なウェイト値に色付けして表示します。  
合計1.0以下 → 赤  
合計1.0以上 → オレンジ  
指定インフルエンス数以上の使用 →　黄色  
上図ボタンから不正頂点ウェイトの絞り込み表示ができます。  
![siweighteditor3](https://user-images.githubusercontent.com/28256498/41658498-78b4f0f2-74d1-11e8-9ea2-7762382a7ee6.gif)

### 
![image](https://user-images.githubusercontent.com/28256498/41657816-8c1e1706-74cf-11e8-8a4d-5c54bbbdb838.png)
