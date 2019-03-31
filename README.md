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

インストールに成功するとウィンドウ以下に項目が追加されます。  

![image](https://user-images.githubusercontent.com/28256498/41663300-0ba78a1c-74de-11e8-82b6-fcc5f1435931.png)


## 主な機能・UI

### 基本UI表示1
![image](https://user-images.githubusercontent.com/28256498/41656766-14a74cae-74cc-11e8-8226-e19d64a98ae2.png)

・Show → 選択したテーブルセルに表示をフォーカスする。  
・Show All → オブジェクトのウェイトを全表示する  
・Focus　→ コンポーネント選択をセル表示に反映する  
・Filter → 表示されているインフルエンスのうちウェイト合計が0のものを非表示にする  
・Highlite → セル選択された頂点をビューポート上でハイライトする  

![siweighteditor1](https://user-images.githubusercontent.com/28256498/41657246-b371c3e0-74cd-11e8-8dbd-5a5b3828902c.gif)

### 基本UI表示2
![image](https://user-images.githubusercontent.com/28256498/41657474-6d59d6d0-74ce-11e8-964c-095097aeb6a3.png)

・鍵マーク　→ メッシュ選択変更のUIへの反映をロックします。一時的にウェイトエディタ表示の更新を止めたい場合に  
・サイクルマーク　→ 現在の選択をUIに反映します。鍵マークでロックがかかっていても強制的に反映  
・Cマーク　→ 表示のクリア  
・⇄マーク　→ セル上の選択頂点を実際に選択し、UI表示も絞り込みます。  
・0-1　→ ウェイトを0.0～1.0で表示します（Maya仕様）  
・0-100　→ ウェイトを0.0～100.0で表示します（SI仕様）  

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

・Enforce Limit →　ここで指定した数以上のインフルエンスを使用している頂点を黄色く表示。
Enforceボタンを押すと自動的に指定数にウェイトを修正します。  
何も選択せずに実行すると全ての頂点に対して修正を実行します。  

・Displayd Digit → 小数点以下の表示桁数を指定  

・Round Off →　指定桁数以下の端数を四捨五入します。  
何も選択せずに実行すると全ての頂点に対して実行します。  

![siweighteditor4](https://user-images.githubusercontent.com/28256498/41664495-d59099d4-74e0-11e8-9f81-c24f26e335ea.gif)

### ジョイントハイライト、ジョイント選択機能
![image](https://user-images.githubusercontent.com/28256498/41717078-7f75d1dc-7593-11e8-90ed-0b91ae8c8591.png)

nsrt各ボタン　→　UIのジョイントカラム右クリックするとジョイント選択、その時に適用するSRTマニピュレータを指定します。  
・n → 変更なし  
・s　→　スケール  
・r　→　ローテーション  
・t　→　トランスレーション  
・Joint Hilite →　UI上で選択されているセルに対応するジョイントをハイライト表示します。 

![siweighteditor5](https://user-images.githubusercontent.com/28256498/41659884-732f4480-74d5-11e8-9fd4-677436ad6170.gif)

## 主な機能・入力

### 入力方法4種類  
・スピンボックス　→　ボックス入力、ホイール可能  
・スライダーバー → スライダーバーで値を指定  
・右クリック入力　→　セルを右クリックして小窓に入力、絶対値の場合はクリックしたセルの値を拾います。  
・直接入力　→　セル選択した状態で数値入力を始めるとそのまま小窓入力できます。  

![siweighteditor6](https://user-images.githubusercontent.com/28256498/41660292-a08124e8-74d6-11e8-8182-08b739b68564.gif)

### 入力モード3種類と正規化設定

![image](https://user-images.githubusercontent.com/28256498/41660048-eac2e02e-74d5-11e8-88c2-96a875f6fa80.png)

・Abs　→　絶対値入力、指定した値がそのまま入ります。  
・Add　→　加算入力、現在の値に入力値を加算（減算）します。  
・Add%　→　率加算、現在の値に対して指定比率加算します。例)50に50を指定すると50%の25が加算されて75になります。  
・Normalize　→　入力後の値を正規化するかどうかの設定、有効にすると自動的に合計1.0（100）に正規化されます。  
右クリックで選択セル（何も選択がない場合はすべてのセル）を強制的に正規化します。  
・Unlimited　→　合計1.0（100）以上の値を許容するかどうか。有効にすると入力上限がなくなります。  

![siweighteditor7](https://user-images.githubusercontent.com/28256498/41660848-33edc672-74d8-11e8-98f4-463b333cae0f.gif)

### 固定値入力ボタン

よく使う特定の値を決め打ちで入力するボタンを追加しました  
左クリック → 絶対値入力  
Shift + 左クリック → 加算  
Ctrl + 左クリック → 減算  

![weight_static_value](https://user-images.githubusercontent.com/28256498/55289010-736e0e80-53fb-11e9-8596-8591d924d92d.gif)

### ウェイトロック機能

![image](https://user-images.githubusercontent.com/28256498/41660533-49fe4320-74d7-11e8-9b4e-308fdc654916.png)

・Lock Wt　→　選択したセルのウェイト値をロックします。  
・Unlock Wt　→　選択したセルのウェイト値をアンロックします。  
・Clear locks　→　すべてのウェイトロックを解除します。  
またカラムをダブルクリックすることで列ごとのロック、アンロックを一括トグルできます。  

![siweighteditor8](https://user-images.githubusercontent.com/28256498/41661699-3fc866b2-74da-11e8-969c-1da1644da3a7.gif)

Lock/Unlockボタン右クリックで選択セルのインフルエンスの全頂点ロック機能を追加  
選択状態、表示状態によらずメッシュ全体でインフルエンスロックがかけられます。  

![siweighteditor22](https://user-images.githubusercontent.com/28256498/43036231-481ae026-8d38-11e8-857b-5279265829b2.gif)

## サブツール
ウェイト調整で重宝する機能をサブツール群としてまとめました  

![image](https://user-images.githubusercontent.com/28256498/42167306-9cad957e-7e48-11e8-891e-6db4277ead3a.png)

### ウェイトハンマーとの連携

![image](https://user-images.githubusercontent.com/28256498/41798593-30aaaa52-76a9-11e8-9d23-394b1315fd41.png)

Maya標準機能のウェイトハンマーを選択したセル頂点に対して実行します。  

![siweighteditor11](https://user-images.githubusercontent.com/28256498/41798700-9dc21404-76a9-11e8-9431-b7b69175238e.gif)

### ウェイト値0.0のセルを変更しないウェイトハンマーとスムース

![weight_smooth](https://user-images.githubusercontent.com/28256498/54880859-16b7a480-4e8d-11e9-8ece-db6e44f59fc3.png)

標準機能のスムースをUI上から実行できるようになりました。  

また元のウェイト値が0.0の箇所は値が変わらないカスタムウィトハンマー、ウェイトスムース機能も追加。  
元から使用しているインフルエンスのみでスムージングしたい場合に。  
スムースボタン右クリックでスムース設定ウィンドウを開きます。  

![weight_Hammer_Smooth](https://user-images.githubusercontent.com/28256498/54880725-72812e00-4e8b-11e9-8e3a-23e22faad107.gif)

### スムースの適用率を変える

元の値とスムース後の値の混ぜ率を変更できる機能をつけました  
数値が小さいほどスムース適用率が低くなります  
100の場合は通常スムースと同じ挙動  

![weight_smooth_ratio](https://user-images.githubusercontent.com/28256498/55289071-6c93cb80-53fc-11e9-91e4-6561ecb19cbc.gif)

### スムース設定ウィンドウ

スムースボタンの右クリックから専用ボタンに変更しました  

SSボタンで設定ウィンドウを開きます  

![weight_smooth_option2](https://user-images.githubusercontent.com/28256498/55289072-74537000-53fc-11e9-9d64-d6f1c55965e0.gif)

### Freeze / Freeze_M

![image](https://user-images.githubusercontent.com/28256498/42168224-5c725550-7e4b-11e8-8cfc-988251d9cfb1.png)

・Freeze  
選択オブジェクトのヒストリを全ベイクしたあとデフォーマクラスタとブレンドシェイプを書き戻します。  
デフォーマクラスタ、ブレンドシェイプを保護しつつヒストリをきれいにしたいときに。  

・freeze_M  
選択オブジェクトのヒストリを全ベイクしたあとスキニング、デフォーマクラスタ、ブレンドシェイプを書き戻します。  
スキニング後、頂点追加やラティス変形した場合にかけておくと安心です。  

![siweighteditor14](https://user-images.githubusercontent.com/28256498/42168248-6ed9c12e-7e4b-11e8-8d0a-a8ea541cc9ef.gif)

### Simple Weight Copy / Paste

![image](https://user-images.githubusercontent.com/28256498/42168321-a14d7ede-7e4b-11e8-9e13-f689ce1d01b4.png)

・Simple Weight Copy  
選択オブジェクトのウェイトデータをオブジェクトごとに一時ファイルとして書き出します。  
前回出力分は上書きされます。  

・Simple Weight Paste (Name Index)  
コピーしたウェイトをオブジェクト名と頂点番号で書き戻します。  
バインド情報も書き戻すので事前バインド不要です。  

・Simple Weight Paste (Name Position)※Maya2016以降  
同じくオブジェクト名と頂点座標で書き戻します。  
頂点番号が変わった場合はこちらをご利用ください。  

![siweighteditor15](https://user-images.githubusercontent.com/28256498/42168767-dec8b5c0-7e4c-11e8-938c-0e5731ea7b87.gif)

ウェイトコピー元が1つだけなら名前が違っていてもペーストできるように拡張しました。   
複製メッシュにインデックスペーストしたり、近い形状のものにポジションペーストしたりと使い方が広がります。

![siweighteditor20](https://user-images.githubusercontent.com/28256498/42734004-24f52860-8877-11e8-87cb-f34ea67bf0f9.gif)


### Transfer Weight Multiple

SIのGatorライクなウェイト転写機能です。  

![image](https://user-images.githubusercontent.com/28256498/42168742-d151a078-7e4c-11e8-87ec-103cfbd36e42.png)

・Transfer Weight / Copy  
転送元のメッシュ情報をコピーします。  
複数メッシュ指定可能です。

・Transfer Weight / Paste  
転送元のメッシュからウェイト情報を転写してきます。  
複数メッシュとコンポーネント単位の指定可能です。  

![siweighteditor13](https://user-images.githubusercontent.com/28256498/42169047-a406172e-7e4d-11e8-8f0f-9cfeb50493d2.gif)

### Move Influence Weight

インフルエンスに割り振られているウェイトを他のインフルエンスに分配する機能です。  

![image](https://user-images.githubusercontent.com/28256498/45917719-c39d6e80-beb6-11e8-979d-2b99b94d502c.png)

使わなくなったジョイントのウェイトを他のジョイントに分配したり、追加したジョイントに振り分けたりなど。  

複数インフルエンスから複数インフルエンスの移動にも対応しています。  

![weight3](https://user-images.githubusercontent.com/28256498/45917665-014dc780-beb6-11e8-8b7c-f1342be82107.gif)

### Vertex Weight Copy / Paste

![weight_vtx_cp](https://user-images.githubusercontent.com/28256498/54880877-3e0e7180-4e8d-11e9-8ade-e456ebb1f537.png)

頂点単位でのウェイト移植機能です。  

標準機能と違い、複数の頂点コピー→複数の頂点ペーストに対応しています。  
ペースト頂点がコピー頂点より多い場合は最初の値に戻って繰り返しペーストされます。  
ウェイトロック機能とは併用不可です。  

またペースト先にインフルエンスが設定されていない場合は自動追加されます。  

![weight_vtx_copy](https://user-images.githubusercontent.com/28256498/54880762-081cbd80-4e8c-11e9-8930-395ca1e04faf.gif)

### Excel like Cell Copy / Paste

![weight_cell_cp](https://user-images.githubusercontent.com/28256498/54880884-5c746d00-4e8d-11e9-8448-5c5ee79c8b4d.png)

エクセルライクな範囲セルのコピー/ペースト機能です。  

指定範囲をコピーして、インフルエンスの違いにかかわらず範囲ペーストができます。  
矩形だけでなく飛び地選択でのコピーペーストも可能。  
ペースト範囲がコピー範囲より大きい場合は繰り返しペーストされます。 
ウェイトロックとの併用も可能です。   

![weight_cell_copy](https://user-images.githubusercontent.com/28256498/54880791-634eb000-4e8c-11e9-8652-28c6f5d973a0.gif)

こちらの機能は右クリックメニューからも呼び出し可能です。  
セルの範囲内では ctrl or shift + 右クリックで呼び出しです。(右クリック入力とかぶるため)  
セルの範囲外は直接右クリックでOK。  

![weight_cell_copy_menu](https://user-images.githubusercontent.com/28256498/54880830-bfb1cf80-4e8c-11e9-8d60-240699a2e092.gif)

###  Symmetry機能

よく使うミラーリング系ツール

![image](https://user-images.githubusercontent.com/28256498/42169176-eeb59ccc-7e4d-11e8-9e1a-e503f51a2b18.png)

・Weight_Symmetrize  
選択した頂点ウェイトを反転命名規則に従ってジョイントラベルを設定しミラーリングします。  
対象メッシュがバインドされていなくても自動バインドするので事前設定不要です。  
メッシュ単位、コンポーネント単位どちらでも実行できます。  
右クリックで命名規則ウィンドウが開きます。  

選択メッシュが1つの時→ +X ⇄ -X どちらに転送するかウィンドウが開きます  
選択メッシュが複数の時→　最初に選択したメッシュのウェイト情報を残りに反転転写します。  
選択コンポーネントの時→　反対のグローバル座標のコンポーネントから反転してきます。  

・Auto_Symmetry  
メッシュ反転からウェイトミラーまで自動。  
こちらもジョイントラベリング、バインド、ミラーまで一括です。  
右クリックで命名規則ウィンドウが開きます。 

スキンメッシュだけでなく、ジョイントやロケータ等なんでも反転できます。

・Mesh Marge with Skinning  
スキニングを保ったままメッシュを結合します。  
機能でもできなくないですが、スキンクラスタを共有するのでノンデフォーマヒストリ削除後のアンドゥなどが非常に不安定なので独自機能として実装しています。  
Auto_Symmetry後に簡単に左右結合ができたりします。  

![siweighteditor16](https://user-images.githubusercontent.com/28256498/42170172-ba98a044-7e50-11e8-90ee-2802d230c857.gif)

・ジョイント左右命名規則エディタの使い方  
右クリックで設定ウィンドウを開きラベリングルールを設定します。  
左右対になるようにPrefix, Suffix, middle_nameを設定します。  
正規表現検索するのでワイルドカードは . (ピリオド)で指定できます。  

例）_L01　⇄ _R01 を対にしたい場合はそれぞれ  
_L01 →　_L..  
_R01 → _R..  
と記入します。  

![image](https://user-images.githubusercontent.com/28256498/42170704-43509d6e-7e52-11e8-91a6-edeb28609531.png)

### Toggle Mute Skinning / Go to Bind Pose 

![image](https://user-images.githubusercontent.com/28256498/42170017-575c39a0-7e50-11e8-996a-87293e8053bb.png)

・Toggle Mute Skinning
選択したメッシュのスキニングのミュートを一括トグル。
何も選択せずに実行でシーン内のメッシュに全適用。

・Go to Bind Pose 
標準機能のバインドポーズに戻るを実行します。

![siweighteditor18](https://user-images.githubusercontent.com/28256498/42170480-96990840-7e51-11e8-8319-881e7e91305d.gif)

### Go Maya Export / Import

Mayaシーン間でのオブジェクトの受け渡し補助ツールです。  
毎回場所を指定して出力したり読み込むのがめんどくさいので。
スキンメッシュはデタッチしないとジョイント階層がついてくるのでFreezeとSimple Weight Copy/Pasteを併用すると便利です。

![image](https://user-images.githubusercontent.com/28256498/42170072-7523953c-7e50-11e8-9887-317a9c11cdd1.png)

・Go Maya Export  
所定の場所に選択オブジェクトを書き出します。
前回出力分は上書きされます。

・Go Maya Import  
GoMayaExportで出力したオブジェクトを読み込みます。

![siweighteditor19](https://user-images.githubusercontent.com/28256498/42170922-d80072fe-7e52-11e8-965d-80fc76fcb114.gif)

### Add Influence / Remove Influence

UI上の選択からスキンに対してインフルエンスの追加削除ができます。  
ジョイントとメッシュを直接選択した状態でも実行可能です。  

![weight1](https://user-images.githubusercontent.com/28256498/45583890-04204980-b905-11e8-8719-2dda7bbcafc4.png)

### Remove Unused Influences
![weight_rem_unuse_inf](https://user-images.githubusercontent.com/28256498/54880904-96457380-4e8d-11e9-96de-4a046d8d4a6d.png)

使用していないインフルエンスの削除。標準機能の呼び出しです。  

![weight_remove_unuse_inf](https://user-images.githubusercontent.com/28256498/54880893-7ada6880-4e8d-11e9-8044-3f4d3204d88b.gif)

## オプション機能

### 0セルの明るさ指定、インフルエンスサーチ
![image](https://user-images.githubusercontent.com/28256498/41661612-12c4e19a-74da-11e8-8a9f-61b90b04f617.png)

・☀マーク　→　値がゼロのカラムの文字色の明るさを指定します。  
・Search →　インフルエンスを絞り込んだり、非表示になっているものを一時的に表示したりします。  
・入力文字で検索、スペースで＆検索、大文字小文字区別なし  
・Refine →　絞り込み検索、現在表示中のインフルエンスから探します。  
・Add → 加算検索、現在非表示のインフルエンスから検索にかかったものを加えて表示します。Filterでゼロカラム非表示状態で使用するととても便利です。オヌヌメ。  
・i マーク →　検索をインタラクティブに行うかどうか。有効にすると文字入力に合わせてリアルタイム検索します。  

![siweighteditor9](https://user-images.githubusercontent.com/28256498/41662504-47b089fc-74dc-11e8-9bd5-aa5294c20491.gif)


