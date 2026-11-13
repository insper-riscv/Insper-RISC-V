//! Alignment-preserving adapter over C malloc/free. No target addresses.
use core::{
    alloc::{GlobalAlloc, Layout},
    ffi::c_void,
    mem::size_of,
    ptr,
};

unsafe extern "C" {
    fn malloc(size: usize) -> *mut c_void;
    fn free(pointer: *mut c_void);
}

/// A stateless allocator using the C heap configured by the platform linker.
pub struct LibcAllocator;

impl LibcAllocator {
    /// Construct the allocator; does not allocate or reset the C heap.
    /// ```
    /// let allocator = rv32_runtime::allocator::LibcAllocator::new();
    /// ```
    pub const fn new() -> Self {
        Self
    }
}

impl Default for LibcAllocator {
    fn default() -> Self {
        Self::new()
    }
}

// SAFETY: each allocation reserves a header and enough alignment padding.
// Deallocation recovers exactly the original malloc pointer. libc provides
// the platform heap; callers must not invoke this foreground allocator in IRQs.
unsafe impl GlobalAlloc for LibcAllocator {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        let header = size_of::<*mut u8>();
        let total = match layout
            .size()
            .checked_add(header)
            .and_then(|size| size.checked_add(layout.align() - 1))
        {
            Some(size) if size <= isize::MAX as usize => size,
            _ => return ptr::null_mut(),
        };
        unsafe {
            let base = malloc(total).cast::<u8>();
            if base.is_null() {
                return ptr::null_mut();
            }
            let start = base.add(header);
            let padding = start.align_offset(layout.align());
            if padding == usize::MAX {
                free(base.cast());
                return ptr::null_mut();
            }
            let aligned = start.add(padding);
            aligned.sub(header).cast::<*mut u8>().write_unaligned(base);
            aligned
        }
    }

    unsafe fn dealloc(&self, pointer: *mut u8, _layout: Layout) {
        unsafe {
            let base = pointer
                .sub(size_of::<*mut u8>())
                .cast::<*mut u8>()
                .read_unaligned();
            free(base.cast());
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn alignment_zeroing_reallocation_and_free() {
        let allocator = LibcAllocator::new();
        for alignment in [1, 2, 4, 8, 16, 64, 256, 4096] {
            let layout = Layout::from_size_align(37, alignment).unwrap();
            unsafe {
                let memory = allocator.alloc_zeroed(layout);
                assert!(!memory.is_null());
                assert_eq!(memory as usize % alignment, 0);
                for index in 0..37 {
                    assert_eq!(memory.add(index).read(), 0);
                    memory.add(index).write(index as u8);
                }
                let grown = allocator.realloc(memory, layout, 79);
                assert!(!grown.is_null());
                assert_eq!(grown as usize % alignment, 0);
                for index in 0..37 {
                    assert_eq!(grown.add(index).read(), index as u8);
                }
                allocator.dealloc(grown, Layout::from_size_align(79, alignment).unwrap());
            }
        }
    }

    #[test]
    fn header_overflow_returns_null() {
        let layout = Layout::from_size_align(isize::MAX as usize, 1).unwrap();
        assert!(unsafe { LibcAllocator::new().alloc(layout) }.is_null());
    }
}
