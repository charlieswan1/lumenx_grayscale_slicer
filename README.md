# lumenx_grayscale_slicer

This tool turns a multi-part 3D model (`.3mf`) into a stack of grayscale PNG images  layers that the CELLINK LumenX Gen-3 printer can use.

Unlike standard `.stl` slicers that only output solid black-and-white images, this tool lets you assign custom `0–255` grayscale UV exposure intensities to different parts of your model (for example, printing half of a part at 100% UV intensity and the other half at 50% UV intensity) while keeping everything aligned and centered on the build plate.

*(Inspired by [bamm_slice](https://github.com/namitn04/bamm_slice).)*

I’ve included a sample file so you can test it right away:
- `Test_Gray.3mf` — a sample two-part 3D model (`5 mm × 7 mm × .5 mm`)

---

## 0) Download this project (no Git needed)
1. On the GitHub page, click the green **Code** button → **Download ZIP**.
2. Double-click the ZIP file to unzip it.
3. You now have a folder (probably called `lumenx_grayscale_slicer-main`). We’ll use that.

---

## 1) Make sure you have Python 3
1. Open **Terminal**
   - Press `Command + Space`, type **Terminal**, hit **Enter**.
2. In Terminal, type:

       python3 --version

   - If you see something like `Python 3.10.9`, you’re good.
   - If you get an error, ask someone or ChatGPT to help install Python 3 (it’s quick).
   - Terminal might prompt you to install python as well

---

## 2) Open Terminal in the project folder
Do this the easy way:
1. In **Finder**, open the `lumenx_grayscale_slicer-main` folder (the one you unzipped).
2. In Terminal, type `cd `.
3. Drag the `lumenx_grayscale_slicer-main` folder from Finder into the Terminal window (this pastes its full path).
4. Press **Enter**.

Your Terminal line should now end with `…/lumenx_grayscale_slicer-main %`

---

## 3) Install the required packages (one copy-paste line)
In Terminal, paste this and press **Enter**:

    python3 -m pip install trimesh pillow numpy shapely scipy networkx rtree lxml

- If that doesn’t work, try:

      pip install trimesh pillow numpy shapely scipy networkx rtree lxml

- If you see a lot of text — that’s normal. Wait until it finishes.

---

## 4) Run the test (just copy and paste)
Make sure you are in the `lumenx_grayscale_slicer-main` folder in Terminal, then run:

    python3 slice_grayscale_3mf.py \
      --input Test_Gray.3mf \
      --layer-mm 0.1 \
      --part-grays 255 128 \
      --out ./Test_Output

**What this does:**
- Uses the included `Test_Gray.3mf` two-part model
- Slices the model into **0.1 mm** (100 µm) layers
- Assigns **Part 1** bright white (`255` = 100% UV exposure) and **Part 2** medium gray (`128` = 50% UV exposure)
- Saves PNG images into a new folder called **Test_Output**

The output folder (`./Test_Output`) will be created automatically if it doesn’t exist.

---

## 5) Check that it worked
- In Finder, open the **Test_Output** folder that was just created.
- You should see a bunch of files named like `layer_0001.png`, `layer_0002.png`, etc.
- Open a few — black is empty background, bright white is 100% UV exposure, and gray is reduced UV exposure.

---

## 6) Use your own Onshape / CAD model next time
When you’re ready to slice a different model:
1. In CAD (such as **Onshape**), design your regions as separate parts in the same Part Studio so they stay aligned.
2. Right-click your Part Studio tab → **Export...** and set the format to **3MF**.
3. Put your `.3mf` file into this same folder (or note where it lives).
4. Run the command again, changing the file names and gray values:

**If everything is in the same folder (easy):**

    python3 slice_grayscale_3mf.py \
      --input "MyModel.3mf" \
      --layer-mm 0.1 \
      --part-grays 255 128 \
      --out ./MyModel_Output

**If your files are elsewhere (full/absolute paths):**
- On a Mac, you can *drag a file from Finder into Terminal* to paste its full path.

      python3 /Users/yourname/Desktop/lumenx_grayscale_slicer-main/slice_grayscale_3mf.py \
        --input /Users/yourname/Desktop/Models/MyModel.3mf \
        --layer-mm 0.1 \
        --part-grays 255 128 \
        --out /Users/yourname/Desktop/MyModel_Output

---

## What the options mean (plain English)
- `--input` — your input 3D model (`.3mf` file)
- `--layer-mm` — thickness of each layer in millimeters. Common values:
  - `0.05` (50 µm, finer, more layers)
  - `0.1` (100 µm, default for quick tests)
- `--part-grays` — space-separated brightness values (`0` to `255`) for **Part 1**, **Part 2**, etc.:
  - `255` = 100% white (full UV intensity)
  - `191` = 75% gray
  - `128` = 50% gray
  - `64` = 25% gray
  - `0` = Black (no exposure)
  - *(Tip: If two parts end up swapped in brightness, just reverse the order of the numbers)*
- `--scale` — unit multiplier (defaults to `1000.0` because Onshape exports `.3mf` files in meters internally; if your CAD software exports in millimeters, add `--scale 1`)
- `--out` — where to save the PNG layers (a folder you name)

**Quick help at any time:**

    python3 slice_grayscale_3mf.py -h

---

## Common problems (and quick fixes)

**Q: “command not found: python3”**  
A: Python 3 isn’t installed or not in PATH. Install Python 3, then try again.

**Q: “No module named …” or “module not found”**  
A: Re-run the install step:

    python3 -m pip install trimesh pillow numpy shapely scipy networkx rtree lxml

**Q: “No such file or directory: Test_Gray.3mf”**  
A: You’re not in the right folder or not referencing the right file path.
- Either `cd` into the correct folder (see Step 2), *or* use full paths by dragging files into Terminal.

**Q: The output folder is empty / not many layers**  
A: Your `--layer-mm` might be too big, or your CAD software exported in millimeters instead of meters. Try adding `--scale 1` or lowering `--layer-mm 0.05`.

**Q: The gray and white parts are flipped**  
A: Reverse the order of numbers after `--part-grays` (for example, change `--part-grays 255 128` to `--part-grays 128 255`) and run it again.

**Q: The model looks off-center in slices**  
A: The script auto-centers the entire assembly on the build plate for you; if something looks odd, check that your model fits the build area (see below).

---

## Safety fit: does your model fit the printer?
This script uses a build area of **68 mm × 38 mm × 100 mm** and a pixel pitch of **0.035 mm** (35 µm, outputting `1943 × 1086 px` PNGs) for the **CELLINK LumenX Gen-3**.  
If your model is larger than that XY area, scale it down in your CAD before slicing.
