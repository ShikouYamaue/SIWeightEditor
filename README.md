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

## 主な機能・UI

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

### 小数点表示桁数と丸め、インフルエンス数の修正
![image](https://user-images.githubusercontent.com/28256498/41657816-8c1e1706-74cf-11e8-8a4d-5c54bbbdb838.png)

Enforce Limit →　ここで指定した数以上のインフルエンスを使用している頂点を黄色く表示。
Enforceボタンを押すと自動的に指定数にウェイトを修正します。　　
何も選択せずに実行すると全ての頂点に対して修正を実行します。  

Displayd Digit → 小数点以下の表示桁数を指定  

Round Off →　指定桁数以下の端数を四捨五入します。  
何も選択せずに実行すると全ての頂点に対して実行します。  

![image](https://user-images.githubusercontent.com/28256498/41659037-2905c37c-74d3-11e8-8d57-7ef070a6ed94.png)

### ジョイントハイライト、ジョイント選択機能
nsrt各ボタン　→　UIのジョイントカラム右クリックするとジョイント選択、その時に適用するSRTマニピュレータを指定します。  
n → 変更なし  
s　→　スケール  
r　→　ローテーション  
t　→　トランスレーション  
Joint Hilite →　UI上で選択されているセルに対応するジョイントをハイライト表示します。 

![siweighteditor5](https://user-images.githubusercontent.com/28256498/41659884-732f4480-74d5-11e8-9fd4-677436ad6170.gif)

## 主な機能・入力

###　入力方法4種類  
スピンボックス　→　ボックス入力、ホイール可能  
スライダーバー → スライダーバーで値を指定  
右クリック入力　→　セルを右クリックして小窓に入力、絶対値の場合はクリックしたセルの値を拾います。  
直接入力　→　セル選択した状態で数値入力を始めるとそのまま小窓入力できます。  

![siweighteditor6](https://user-images.githubusercontent.com/28256498/41660292-a08124e8-74d6-11e8-8182-08b739b68564.gif)

### 入力モード3種類と正規化設定

![image](https://user-images.githubusercontent.com/28256498/41660048-eac2e02e-74d5-11e8-88c2-96a875f6fa80.png)

Abs　→　絶対値入力、指定した値がそのまま入ります。  
Add　→　加算入力、現在の値に入力値を加算（減算）します。  
Add%　→　率加算、現在の値に対して指定比率加算します。例)50に50を指定すると50%の25が加算されて75になります。  
Normalize　→　入力後の値を正規化するかどうかの設定、有効にすると自動的に合計1.0（100）に正規化されます。  
Unlimited　→　合計1.0（100）以上の値を許容するかどうか。有効にすると入力上限がなくなります。  

![siweighteditor7](https://user-images.githubusercontent.com/28256498/41660848-33edc672-74d8-11e8-98f4-463b333cae0f.gif)

### ウェイトロック機能

![image](https://user-images.githubusercontent.com/28256498/41660533-49fe4320-74d7-11e8-9b4e-308fdc654916.png)

Lock Wt　→　選択したセルのウェイト値をロックします。  
Unlock Wt　→　選択したセルのウェイト値をアンロックします。  
Clear locks　→　すべてのウェイトロックを解除します。  
またカラムをダブルクリックすることで列ごとのロック、アンロックを一括トグルできます。  

![siweighteditor8](https://user-images.githubusercontent.com/28256498/41661699-3fc866b2-74da-11e8-969c-1da1644da3a7.gif)

## オプション機能

### 0セルの明るさ指定、インフルエンスサーチ
![image](https://user-images.githubusercontent.com/28256498/41661612-12c4e19a-74da-11e8-8a9f-61b90b04f617.png)

☀マーク　→　値がゼロのカラムの文字色の明るさを指定します。  
Search →　インフルエンスを絞り込んだり、非表示になっているものを一時的に表示したりします。  
入力文字で検索、スペースで＆検索、大文字小文字区別なし  
iマーク →　検索をインタラクティブに行うかどうか。有効にすると文字入力に合わせてリアルタイム検索します。  















