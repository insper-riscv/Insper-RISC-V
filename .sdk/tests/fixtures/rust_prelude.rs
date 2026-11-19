#![no_std]
#![no_main]

use rv32_runtime::{entry, prelude::*};

entry!(main);

fn main() {
    let current_val: usize = 42;
    assert_eq!(current_val.to_string(), "42");
    assert_eq!(usize::MAX.to_string().parse::<usize>(), Ok(usize::MAX));

    // The alloc namespace is also available for explicit standard imports.
    {
        use alloc::string::ToString;

        assert_eq!(123_usize.to_string(), "123");
    }

    let mut text = "value=".to_owned();
    write!(&mut text, "{}", current_val).unwrap();
    writeln!(&mut text, "; ready").unwrap();
    assert_eq!(text, "value=42; ready\n");
    assert_eq!(format!("{:04}", 7), "0007");

    let mut map = BTreeMap::new();
    map.insert(1_usize, text);
    let keys: BTreeSet<_> = map.keys().copied().collect();
    assert!(keys.contains(&1));

    let mut queue = VecDeque::new();
    queue.push_back(Box::new(7));
    assert_eq!(queue.pop_front().map(|item| *item), Some(7));

    let shared = Rc::new("shared".to_owned());
    let other = Rc::clone(&shared);
    assert_eq!(Rc::strong_count(&other), 2);
    let label: Cow<'_, str> = Cow::Borrowed(&other);
    assert_eq!(label.into_owned(), "shared");

    // Keep the established runtime smoke output unchanged.
    let mut values = vec![1_u32, 2, 3];
    values.push(4);
    let message = "Hello from an RV32 Rust project.".to_owned();
    println!("{}", message);
    println!("values = {:?}", values);
}
