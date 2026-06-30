#[derive(Debug, Clone, PartialEq)]
pub enum Value {
    Null,
    Integer(i64),
    Real(f64),
    Text(String),
    Blob(Vec<u8>),
    Vector(Vec<f32>),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ValueType {
    Null,
    Integer,
    Real,
    Text,
    Blob,
    Vector,
}

impl Value {
    pub fn null() -> Self {
        Self::Null
    }

    pub fn integer(value: i64) -> Self {
        Self::Integer(value)
    }

    pub fn real(value: f64) -> Self {
        Self::Real(value)
    }

    pub fn text(value: impl Into<String>) -> Self {
        Self::Text(value.into())
    }

    pub fn blob(value: impl Into<Vec<u8>>) -> Self {
        Self::Blob(value.into())
    }

    pub fn vector(value: impl Into<Vec<f32>>) -> Self {
        Self::Vector(value.into())
    }

    pub fn value_type(&self) -> ValueType {
        match self {
            Self::Null => ValueType::Null,
            Self::Integer(_) => ValueType::Integer,
            Self::Real(_) => ValueType::Real,
            Self::Text(_) => ValueType::Text,
            Self::Blob(_) => ValueType::Blob,
            Self::Vector(_) => ValueType::Vector,
        }
    }

    pub fn is_null(&self) -> bool {
        matches!(self, Self::Null)
    }

    pub fn as_integer(&self) -> Option<i64> {
        match self {
            Self::Integer(value) => Some(*value),
            _ => None,
        }
    }

    pub fn as_real(&self) -> Option<f64> {
        match self {
            Self::Real(value) => Some(*value),
            _ => None,
        }
    }

    pub fn as_text(&self) -> Option<&str> {
        match self {
            Self::Text(value) => Some(value.as_str()),
            _ => None,
        }
    }

    pub fn as_blob(&self) -> Option<&[u8]> {
        match self {
            Self::Blob(value) => Some(value.as_slice()),
            _ => None,
        }
    }

    pub fn as_vector(&self) -> Option<&[f32]> {
        match self {
            Self::Vector(value) => Some(value.as_slice()),
            _ => None,
        }
    }

    pub fn vector_dim(&self) -> Option<usize> {
        self.as_vector().map(<[f32]>::len)
    }
}

impl From<i64> for Value {
    fn from(value: i64) -> Self {
        Self::integer(value)
    }
}

impl From<f64> for Value {
    fn from(value: f64) -> Self {
        Self::real(value)
    }
}

impl From<String> for Value {
    fn from(value: String) -> Self {
        Self::text(value)
    }
}

impl From<&str> for Value {
    fn from(value: &str) -> Self {
        Self::text(value)
    }
}

impl From<Vec<u8>> for Value {
    fn from(value: Vec<u8>) -> Self {
        Self::blob(value)
    }
}

impl From<&[u8]> for Value {
    fn from(value: &[u8]) -> Self {
        Self::blob(value)
    }
}

impl From<Vec<f32>> for Value {
    fn from(value: Vec<f32>) -> Self {
        Self::vector(value)
    }
}

impl From<&[f32]> for Value {
    fn from(value: &[f32]) -> Self {
        Self::vector(value)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn value_type_matches_each_value_variant() {
        let cases = [
            (Value::null(), ValueType::Null),
            (Value::integer(42), ValueType::Integer),
            (Value::real(3.5), ValueType::Real),
            (Value::text("hello"), ValueType::Text),
            (Value::blob([1, 2, 3]), ValueType::Blob),
            (Value::vector([0.1, 0.2, 0.3]), ValueType::Vector),
        ];

        for (value, expected_type) in cases {
            assert_eq!(value.value_type(), expected_type);
        }
    }

    #[test]
    fn scalar_accessors_only_match_their_own_type() {
        let integer = Value::integer(7);
        let real = Value::real(1.25);
        let text = Value::text("owned text");

        assert_eq!(integer.as_integer(), Some(7));
        assert_eq!(integer.as_real(), None);
        assert_eq!(real.as_real(), Some(1.25));
        assert_eq!(real.as_integer(), None);
        assert_eq!(text.as_text(), Some("owned text"));
        assert_eq!(text.as_integer(), None);
    }

    #[test]
    fn text_blob_and_vector_hold_owned_data() {
        let source_text = String::from("hello");
        let source_blob = vec![1, 2, 3];
        let source_vector = vec![0.25, 0.5];

        let text = Value::text(source_text.clone());
        let blob = Value::blob(source_blob.clone());
        let vector = Value::vector(source_vector.clone());

        assert_eq!(text.as_text(), Some(source_text.as_str()));
        assert_eq!(blob.as_blob(), Some(source_blob.as_slice()));
        assert_eq!(vector.as_vector(), Some(source_vector.as_slice()));
    }

    #[test]
    fn vector_dimension_is_available_only_for_vectors() {
        let vector = Value::vector(vec![1.0, 2.0, 3.0, 4.0]);

        assert_eq!(vector.vector_dim(), Some(4));
        assert_eq!(Value::null().vector_dim(), None);
        assert_eq!(Value::text("not a vector").vector_dim(), None);
    }

    #[test]
    fn null_is_only_null() {
        let value = Value::null();

        assert!(value.is_null());
        assert_eq!(value.value_type(), ValueType::Null);
        assert_eq!(value.as_integer(), None);
        assert_eq!(value.as_real(), None);
        assert_eq!(value.as_text(), None);
        assert_eq!(value.as_blob(), None);
        assert_eq!(value.as_vector(), None);
        assert_eq!(value.vector_dim(), None);
    }

    #[test]
    fn conversions_create_expected_value_variants() {
        assert_eq!(Value::from(1_i64), Value::Integer(1));
        assert_eq!(Value::from(2.5_f64), Value::Real(2.5));
        assert_eq!(Value::from("abc"), Value::Text(String::from("abc")));
        assert_eq!(Value::from(vec![1_u8, 2]), Value::Blob(vec![1, 2]));
        assert_eq!(
            Value::from(vec![1.0_f32, 2.0]),
            Value::Vector(vec![1.0, 2.0])
        );
    }
}
