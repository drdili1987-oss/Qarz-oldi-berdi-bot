import codecs

def patch_file():
    with codecs.open('handlers/debts.py', 'r', 'utf-8') as f:
        content = f.read()
    
    with codecs.open('temp_debts.py', 'r', 'utf-8') as f:
        new_logic = f.read()

    start_str = '@router.message(AddDebt.entering_description, F.text)'
    end_str = '    await state.clear()\n\n\n@router.callback_query(F.data.startswith("debt_confirm_"))'
    
    start_idx = content.find(start_str)
    end_idx = content.find(end_str)
    
    if start_idx == -1 or end_idx == -1:
        print(f"Error finding indices. Start: {start_idx}, End: {end_idx}")
        # Try alternate end string if it didn't match exactly
        end_str2 = '@router.callback_query(F.data.startswith("debt_confirm_"))'
        end_idx = content.find(end_str2)
        print(f"Fallback end_idx: {end_idx}")
        if start_idx == -1 or end_idx == -1:
            return

    new_content = content[:start_idx] + new_logic + "\n\n" + content[end_idx:]
    
    with codecs.open('handlers/debts.py', 'w', 'utf-8') as f:
        f.write(new_content)
    
    print("Patch applied successfully!")

if __name__ == '__main__':
    patch_file()
