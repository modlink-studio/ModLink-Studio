import {useCallback, useState} from "react";

type LineEditorApi = {
  value: string;
  begin: (initialValue: string) => void;
  append: (input: string) => void;
  backspace: () => void;
  clear: () => void;
};

export function useLineEditor(): LineEditorApi {
  const [value, setValue] = useState("");

  const begin = useCallback((initialValue: string) => {
    setValue(initialValue);
  }, []);

  const append = useCallback((input: string) => {
    setValue((currentValue) => currentValue + input);
  }, []);

  const backspace = useCallback(() => {
    setValue((currentValue) => currentValue.slice(0, -1));
  }, []);

  const clear = useCallback(() => {
    setValue("");
  }, []);

  return {value, begin, append, backspace, clear};
}
