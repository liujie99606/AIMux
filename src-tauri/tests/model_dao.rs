use aimux_lib::{
    dao::model_dao::{create, get, set_default},
    database::connect,
    schema::model_schema::ModelCreate,
};

#[tokio::test]
async fn switches_the_only_default_model_in_a_transaction() {
    let path = std::env::temp_dir().join(format!(
        "aimux-model-default-{}.sqlite3",
        uuid::Uuid::new_v4()
    ));
    let pool = connect(&path).await.expect("创建数据库失败");
    let first = create(
        &pool,
        ModelCreate {
            name: "model-a".into(),
            model_type: "openai".into(),
        },
    )
    .await
    .expect("创建第一个模型失败");
    let second = create(
        &pool,
        ModelCreate {
            name: "model-b".into(),
            model_type: "openai".into(),
        },
    )
    .await
    .expect("创建第二个模型失败");
    set_default(&pool, first)
        .await
        .expect("设置第一个默认模型失败");
    let duplicate_default = sqlx::query("UPDATE models SET is_default=1 WHERE id=?")
        .bind(&second.id)
        .execute(&pool)
        .await;
    assert!(duplicate_default.is_err());
    set_default(&pool, second.clone())
        .await
        .expect("切换默认模型失败");
    let defaults: i64 =
        sqlx::query_scalar("SELECT COUNT(*) FROM models WHERE type='openai' AND is_default=1")
            .fetch_one(&pool)
            .await
            .expect("读取默认模型数量失败");
    assert_eq!(defaults, 1);
    assert_eq!(
        get(&pool, &second.id)
            .await
            .expect("读取第二个模型失败")
            .expect("第二个模型不存在")
            .is_default,
        1
    );
    pool.close().await;
    let _ = std::fs::remove_file(path);
}
