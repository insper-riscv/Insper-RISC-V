//! Consumer tests deliberately use the core prelude rather than std's prelude.
#![no_std]

use rv32_runtime::prelude::*;

#[test]
fn converts_display_values_without_an_explicit_trait_import() {
    assert_eq!(42_usize.to_string(), "42");
    assert_eq!((-17_i32).to_string(), "-17");
    assert_eq!(usize::MAX.to_string().parse::<usize>(), Ok(usize::MAX));
}

#[test]
fn exposes_the_alloc_namespace_without_an_extern_crate_declaration() {
    use alloc::string::ToString;

    let text: alloc::string::String = 123_usize.to_string();
    assert_eq!(text, "123");
}

#[test]
fn clones_borrowed_data_and_formats_into_a_string() {
    let mut text = "value=".to_owned();
    write!(&mut text, "{}", 42).unwrap();
    writeln!(&mut text, "; ready").unwrap();
    assert_eq!(text, "value=42; ready\n");
    assert_eq!(format!("{:04}", 7), "0007");
    assert_eq!([1, 2, 3].to_vec(), vec![1, 2, 3]);
}

#[test]
fn provides_heap_containers_without_os_or_atomic_instructions() {
    let mut map = BTreeMap::new();
    map.insert(2, "second".to_owned());
    map.insert(1, "first".to_owned());
    assert_eq!(map.keys().copied().collect::<Vec<_>>(), vec![1, 2]);

    let set: BTreeSet<_> = [2, 1, 2].into_iter().collect();
    assert_eq!(set.len(), 2);

    let mut queue = VecDeque::new();
    queue.push_back(7);
    queue.push_front(3);
    assert_eq!(queue.pop_front(), Some(3));

    let shared = Rc::new(String::from("shared"));
    let other = Rc::clone(&shared);
    assert_eq!(Rc::strong_count(&other), 2);
    assert_eq!(&**other, "shared");

    let borrowed: Cow<'_, str> = Cow::Borrowed("owned later");
    let owned: Box<str> = borrowed.into_owned().into_boxed_str();
    assert_eq!(&*owned, "owned later");
}
