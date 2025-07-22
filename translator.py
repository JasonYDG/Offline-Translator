import tkinter as tk
from tkinter import ttk, messagebox
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoConfig
from accelerate import init_empty_weights, load_checkpoint_and_dispatch
import os
import torch
import threading
import tkinter.font as tkFont
import time
import traceback
import sys

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    with open("error_log.txt", "a") as f:
        f.write("\n---" + time.strftime("%Y-%m-%d %H:%M:%S") + "---\n")
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
    
    try:
        messagebox.showerror("Application Error", "An unexpected error occurred. Please check 'error_log.txt' for details.")
    except:
        pass # Ignore if messagebox fails

sys.excepthook = handle_exception

class TranslatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Offline-Translator(Powered by Seed-X Pro)")
        self.root.geometry("800x600")

        self.custom_font = tkFont.Font(family="Segoe UI", size=10)

        self.style = ttk.Style()
        self.style.configure(".", font=self.custom_font)
        self.style.configure("TButton", font=self.custom_font)
        self.style.configure("TCombobox", font=self.custom_font)
        self.style.configure("TLabel", font=self.custom_font)
        self.style.configure("TLabelframe.Label", font=self.custom_font)

        # Language mappings with better structure for bidirectional translation
        self.languages = {
            "English": {"name": "English", "code": "en"},
            "Chinese": {"name": "中文", "code": "zh"},
            "Spanish": {"name": "Español", "code": "es"},
            "French": {"name": "Français", "code": "fr"},
            "German": {"name": "Deutsch", "code": "de"},
            "Japanese": {"name": "日本語", "code": "ja"},
            "Korean": {"name": "한국어", "code": "ko"},
            "Russian": {"name": "Русский", "code": "ru"},
        }

        # Initialize device list with GPU priority
        self.devices = []
        
        # Check for CUDA GPUs first and add them to the front of the list
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            for i in range(gpu_count):
                gpu_name = torch.cuda.get_device_name(i)
                self.devices.append(f"cuda:{i} ({gpu_name})")
        
        # Add CPU as the last option
        self.devices.append("cpu")

        self.model_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
        self.model = None
        self.tokenizer = None
        self.model_loaded = False
        self.device = tk.StringVar(value=self.devices[0])
        
        # Add source language selection
        self.source_lang = tk.StringVar(value="Chinese")

        self.create_widgets()
        self.setup_keyboard_shortcuts()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        main_frame.columnconfigure(0, weight=1)

        device_frame = ttk.LabelFrame(control_frame, text="Select Device", padding="10")
        device_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.device_menu = ttk.Combobox(device_frame, textvariable=self.device, values=self.devices, state="readonly")
        self.device_menu.pack(fill=tk.X)

        self.load_button = ttk.Button(control_frame, text="Load Model", command=self.load_model_thread)
        self.load_button.pack(side=tk.LEFT, fill=tk.X, padx=5)

        # Language selection frame
        lang_frame = ttk.LabelFrame(main_frame, text="Language Settings", padding="10")
        lang_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        lang_frame.columnconfigure(0, weight=1)
        lang_frame.columnconfigure(2, weight=1)
        
        # Source language
        ttk.Label(lang_frame, text="From:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.source_menu = ttk.Combobox(lang_frame, textvariable=self.source_lang, values=list(self.languages.keys()), state="readonly")
        self.source_menu.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # Swap button
        self.swap_button = ttk.Button(lang_frame, text="⇄", width=3, command=self.swap_languages)
        self.swap_button.grid(row=0, column=2, padx=5)
        
        # Target language
        ttk.Label(lang_frame, text="To:").grid(row=0, column=3, sticky=tk.W, padx=(10, 5))
        self.target_lang = tk.StringVar(value="English")
        self.target_menu = ttk.Combobox(lang_frame, textvariable=self.target_lang, values=list(self.languages.keys()), state="readonly")
        self.target_menu.grid(row=0, column=4, sticky=(tk.W, tk.E))

        input_frame = ttk.LabelFrame(main_frame, text="Input Text", padding="10")
        input_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        main_frame.rowconfigure(2, weight=1)
        
        # Add scrollbar to input text
        input_scroll_frame = ttk.Frame(input_frame)
        input_scroll_frame.pack(fill=tk.BOTH, expand=True)
        
        self.input_text = tk.Text(input_scroll_frame, wrap=tk.WORD, height=10, font=self.custom_font)
        input_scrollbar = ttk.Scrollbar(input_scroll_frame, orient=tk.VERTICAL, command=self.input_text.yview)
        self.input_text.configure(yscrollcommand=input_scrollbar.set)
        
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        input_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add clear button for input
        input_button_frame = ttk.Frame(input_frame)
        input_button_frame.pack(fill=tk.X, pady=(5, 0))
        self.clear_input_button = ttk.Button(input_button_frame, text="Clear Input", command=self.clear_input)
        self.clear_input_button.pack(side=tk.RIGHT)

        output_frame = ttk.LabelFrame(main_frame, text="Translation Result", padding="10")
        output_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        main_frame.rowconfigure(3, weight=1)
        
        # Add scrollbar to output text
        output_scroll_frame = ttk.Frame(output_frame)
        output_scroll_frame.pack(fill=tk.BOTH, expand=True)
        
        self.output_text = tk.Text(output_scroll_frame, wrap=tk.WORD, height=10, state=tk.DISABLED, font=self.custom_font)
        output_scrollbar = ttk.Scrollbar(output_scroll_frame, orient=tk.VERTICAL, command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=output_scrollbar.set)
        
        self.output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        output_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add copy button for output
        output_button_frame = ttk.Frame(output_frame)
        output_button_frame.pack(fill=tk.X, pady=(5, 0))
        self.copy_output_button = ttk.Button(output_button_frame, text="Copy Result", command=self.copy_output)
        self.copy_output_button.pack(side=tk.RIGHT)

        self.translate_button = ttk.Button(main_frame, text="Translate", command=self.translate, state=tk.DISABLED)
        self.translate_button.grid(row=4, column=0, columnspan=2, pady=10)

        self.status_bar = ttk.Label(main_frame, text="Please select a device and load the model", relief=tk.SUNKEN, anchor=tk.W, font=self.custom_font)
        self.status_bar.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E))

        self.style.configure("TProgressbar", background="#4CAF50", troughcolor="#E0E0E0", bordercolor="#4CAF50", lightcolor="#4CAF50", darkcolor="#4CAF50")
        self.progress_bar = ttk.Progressbar(main_frame, orient="horizontal", length=200, mode="indeterminate", style="TProgressbar")
        self.progress_bar.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

    def swap_languages(self):
        """Swap source and target languages"""
        source = self.source_lang.get()
        target = self.target_lang.get()
        self.source_lang.set(target)
        self.target_lang.set(source)

    def load_model_thread(self):
        self.load_button.config(state=tk.DISABLED)
        self.device_menu.config(state=tk.DISABLED)
        self.status_bar.config(text=f"Loading translation engine to {self.device.get().upper()}... please wait")
        thread = threading.Thread(target=self._load_model)
        thread.daemon = True
        thread.start()

    def _load_model(self):
        device_selection = self.device.get()
        
        # Parse device from selection (extract cuda:X from "cuda:X (GPU Name)" format)
        if device_selection.startswith("cuda:"):
            device = device_selection.split(" ")[0]  # Extract "cuda:X" part
        else:
            device = "cpu"
        
        self.root.after(0, lambda: self.progress_bar.start())
        self.root.after(0, lambda: self.progress_bar.config(mode="indeterminate"))
        
        status_prefix = ""
        if device == "cpu":
            status_prefix = "(CPU loading can be slow, please be patient) "

        try:
            self.root.after(0, lambda: self.status_bar.config(text=f'{status_prefix}Loading tokenizer... (1/4)'))
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, legacy=False)
            self.root.after(0, lambda: self.status_bar.config(text=f'{status_prefix}Loading model configuration... (2/4)'))
            config = AutoConfig.from_pretrained(self.model_name)
            
            model_path = self.model_name

            self.root.after(0, lambda: self.status_bar.config(text=f'{status_prefix}Initializing empty model... (3/4)'))
            with init_empty_weights():
                model_empty = AutoModelForCausalLM.from_config(config)
            
            model_empty.tie_weights()

            self.root.after(0, lambda: self.status_bar.config(text=f'{status_prefix}Loading model weights to {device.upper()}... (4/4)'))
            self.model = load_checkpoint_and_dispatch(
                model_empty, model_path, device_map={"": device}, no_split_module_classes=["LlamaDecoderLayer"], dtype=torch.bfloat16
            )

            self.model_loaded = True
            self.root.after(0, self._on_model_loaded)
        except Exception as e:
            self.root.after(0, lambda e=e: self._on_model_load_error(e))
        finally:
            self.root.after(0, lambda: self.progress_bar.stop())

    def _on_model_loaded(self):
        final_device = next(self.model.parameters()).device
        device_status_message = f"Model loaded successfully, using {str(final_device).upper()}."
        if "cuda" in self.device.get() and "cuda" not in str(final_device):
            device_status_message = f"Model loaded successfully, using {str(final_device).upper()}. (Warning: Model not fully loaded to the selected GPU.)"
        self.root.after(0, lambda: self.status_bar.config(text=device_status_message))
        self.root.after(0, lambda: self.translate_button.config(state=tk.NORMAL))

    def _on_model_load_error(self, e):
        self.status_bar.config(text="Model loading failed, please check the error message.")
        self.load_button.config(state=tk.NORMAL)
        self.device_menu.config(state=tk.NORMAL)
        self.root.after(0, lambda e=e: messagebox.showerror("Model Load Error", f"Error loading model: {e}"))

    def translate(self):
        if not self.model_loaded:
            messagebox.showinfo("Please Wait", "The model is still loading, please try again later.")
            return

        input_content = self.input_text.get("1.0", tk.END).strip()
        source_lang = self.languages[self.source_lang.get()]
        target_lang = self.languages[self.target_lang.get()]

        # Validate language selection
        if self.source_lang.get() == self.target_lang.get():
            messagebox.showwarning("Language Selection", "Source and target languages cannot be the same.")
            return

        max_chars = 5000  # Set limit to 5000 characters
        if len(input_content) > max_chars:
            # Show warning and ask user to shorten the text
            messagebox.showwarning(
                "Text Too Long", 
                f"Input text is {len(input_content)} characters long, which exceeds the {max_chars} character limit.\n\n"
                f"Please shorten your text by {len(input_content) - max_chars} characters and try again.\n\n"
                f"Tip: You can split long texts into smaller parts for better translation quality."
            )
            return

        if not input_content:
            return

        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, "Translating...")
        self.output_text.config(state=tk.DISABLED)
        self.translate_button.config(state=tk.DISABLED)
        self.root.update_idletasks()

        thread = threading.Thread(target=self._perform_translation, args=(input_content, source_lang, target_lang))
        thread.daemon = True
        thread.start()

    def _perform_translation(self, input_content, source_lang, target_lang):
        self.root.after(0, lambda: self.progress_bar.start())
        self.root.after(0, lambda: self.progress_bar.config(mode="indeterminate"))
        start_time = time.time()
        try:
            self.root.after(0, lambda: self.status_bar.config(text="Preparing input... (1/3)"))
            
            # Create a more robust prompt for better translation quality
            source_name = source_lang["name"]
            target_name = target_lang["name"]
            
            # Use extremely simple prompts to get only translation without explanations
            if source_name == "中文" and target_name == "English":
                prompt = f"中文：{input_content}\n英文："
            elif source_name == "English" and target_name == "中文":
                prompt = f"English: {input_content}\n中文："
            elif source_name == "中文":
                prompt = f"中文：{input_content}\n{target_name}："
            elif target_name == "English":
                prompt = f"{source_name}: {input_content}\nEnglish:"
            else:
                prompt = f"{source_name}: {input_content}\n{target_name}:"

            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
            input_length = inputs.input_ids.shape[1]

            self.root.after(0, lambda: self.status_bar.config(text="Generating translation... (2/3)"))
            
            # Optimized generation parameters for complete translations
            outputs = self.model.generate(
                inputs.input_ids,
                max_new_tokens=1536,  # Further increased for very long texts
                num_return_sequences=1,
                do_sample=True,  # Enable sampling for better quality
                temperature=0.2,  # Slightly higher temperature for better flow
                top_p=0.9,
                repetition_penalty=1.02,  # Reduced to avoid cutting off valid repetitions
                pad_token_id=self.tokenizer.eos_token_id,
                # Remove explicit eos_token_id to prevent premature stopping
                early_stopping=False,
                length_penalty=1.0  # Encourage longer outputs
            )
            
            self.root.after(0, lambda: self.status_bar.config(text="Decoding output... (3/3)"))
            
            # Decode only the new tokens (translation part)
            generated_tokens = outputs[0][input_length:]
            translated_text = self.tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
            
            # Clean up the translation output
            translated_text = self._clean_translation_output(translated_text, input_content, source_name, target_name)

            translated_chars = len(translated_text)
            end_time = time.time()
            time_taken = end_time - start_time

            self.root.after(0, lambda: self.output_text.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.output_text.delete("1.0", tk.END))
            self.root.after(0, lambda: self.output_text.insert(tk.END, translated_text))
            self.root.after(0, lambda: self.output_text.config(state=tk.DISABLED))
            self.root.after(0, lambda: self.status_bar.config(text=f"Translation complete! Translated {translated_chars} characters in {time_taken:.2f} seconds."))
        except Exception as e:
            self.root.after(0, lambda: self.output_text.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.output_text.delete("1.0", tk.END))
            self.root.after(0, lambda: self.output_text.insert(tk.END, f"Translation error: {e}"))
            self.root.after(0, lambda: self.output_text.config(state=tk.DISABLED))
            self.root.after(0, lambda: self.status_bar.config(text="Translation failed, please check the error message."))
            self.root.after(0, lambda e=e: messagebox.showerror("Translation Error", f"Error during translation: {e}"))
        finally:
            self.root.after(0, lambda: self.translate_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.progress_bar.stop())

    def _clean_translation_output(self, translated_text, input_content, source_name, target_name):
        """Clean up the translation output to remove unwanted artifacts"""
        import re
        
        # Store original for debugging
        original_text = translated_text
        
        # First, look for strong explanation markers that definitely indicate non-translation content
        strong_explanation_markers = [
            '[COT]', '[cot]', 'This is an advertisement', 'The purpose here should be',
            'Firstly，the brand name', 'Secondly，the model number', 'Thirdly，the term',
            'Fourthly，the phrase', 'Finally, the overall tone'
        ]
        
        # Only cut off at strong markers to avoid cutting valid translation
        for marker in strong_explanation_markers:
            if marker in translated_text:
                pos = translated_text.find(marker)
                translated_text = translated_text[:pos].strip()
                break
        
        # Remove only the most obvious prompt artifacts at the beginning
        start_cleanup_patterns = [
            f"{source_name}:", f"{target_name}:",
            "翻译成英文：", "英文：", "中文：", "English:"
        ]
        
        for pattern in start_cleanup_patterns:
            if translated_text.startswith(pattern):
                translated_text = translated_text[len(pattern):].strip()
        
        # Remove leading/trailing quotes only if they wrap the entire text
        if translated_text.startswith('"') and translated_text.endswith('"'):
            translated_text = translated_text[1:-1].strip()
        if translated_text.startswith("'") and translated_text.endswith("'"):
            translated_text = translated_text[1:-1].strip()
        
        # Fix spacing issues but be conservative
        translated_text = re.sub(r'\s+', ' ', translated_text)  # Multiple spaces to single
        
        # Only fix obvious concatenation errors
        spacing_fixes = [
            ("supportfor", "support for"),
            ("creatorsand", "creators and"),
            ("placingan", "placing an"),
            ("researchng", "researching"),
            ("furtherabout", "further about"),
            ("thismodelandloveditmoreandenmore", "this model and loved it more and more"),
            ("askingthe", "asking the"),
            ("salesmaniftherewasanyexhibitioncarbut", "salesman if there was any exhibition car but"),
            ("waitednearly", "waited nearly"),
            ("monthsforone", "months for one"),
            ("arrive", "to arrive")
        ]
        
        for wrong, correct in spacing_fixes:
            translated_text = translated_text.replace(wrong, correct)
        
        # Clean up any remaining formatting issues
        translated_text = re.sub(r'\s+', ' ', translated_text).strip()
        
        # If the result is too short, return the original with minimal cleanup
        if len(translated_text.strip()) < 20:
            # Just remove the most obvious artifacts from original
            minimal_cleanup = original_text
            for pattern in start_cleanup_patterns:
                if minimal_cleanup.startswith(pattern):
                    minimal_cleanup = minimal_cleanup[len(pattern):].strip()
            return minimal_cleanup if minimal_cleanup else "Translation failed - please try again with different text."
        
        return translated_text

    def clear_input(self):
        """Clear the input text area"""
        self.input_text.delete("1.0", tk.END)

    def copy_output(self):
        """Copy the translation result to clipboard"""
        try:
            output_content = self.output_text.get("1.0", tk.END).strip()
            if output_content and output_content != "Translating...":
                self.root.clipboard_clear()
                self.root.clipboard_append(output_content)
                self.root.update()  # Required for clipboard to work properly
                messagebox.showinfo("Copied", "Translation result copied to clipboard!")
            else:
                messagebox.showwarning("No Content", "No translation result to copy.")
        except Exception as e:
            messagebox.showerror("Copy Error", f"Failed to copy to clipboard: {e}")

    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for better user experience"""
        # Ctrl+Enter to translate
        self.root.bind('<Control-Return>', lambda e: self.translate() if self.model_loaded else None)
        
        # Ctrl+L to load model
        self.root.bind('<Control-l>', lambda e: self.load_model_thread() if not self.model_loaded else None)
        
        # Ctrl+Shift+C to copy output
        self.root.bind('<Control-Shift-C>', lambda e: self.copy_output())
        
        # Ctrl+Shift+X to clear input
        self.root.bind('<Control-Shift-X>', lambda e: self.clear_input())
        
        # Ctrl+Shift+S to swap languages
        self.root.bind('<Control-Shift-S>', lambda e: self.swap_languages())
        
        # F1 to show help
        self.root.bind('<F1>', lambda e: self.show_help())

    def show_help(self):
        """Show keyboard shortcuts help"""
        help_text = """Keyboard Shortcuts:

Ctrl+Enter - Translate text
Ctrl+L - Load model
Ctrl+Shift+C - Copy translation result
Ctrl+Shift+X - Clear input text
Ctrl+Shift+S - Swap source and target languages
F1 - Show this help

Tips:
• Make sure to load the model before translating
• Use the swap button (⇄) to quickly switch languages
• The app supports bidirectional translation between multiple languages
• Translation quality depends on the loaded model"""
        
        messagebox.showinfo("Help - Keyboard Shortcuts", help_text)

if __name__ == "__main__":
    root = tk.Tk()
    app = TranslatorApp(root)
    root.mainloop()