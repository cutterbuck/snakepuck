//! Server only: the data layer, the JSON API and rate limiting. Not compiled into the
//! browser bundle.

pub mod api;
pub mod data;
pub mod games;
pub mod limit;
