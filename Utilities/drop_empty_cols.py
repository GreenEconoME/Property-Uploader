# df as input, return the df without any empty columns
def drop_empty_cols(df):
    empty_cols = []
    for x in df.columns:
        if 'Unnamed' in x:
            empty_cols.append(x)
    df.drop(columns = empty_cols, inplace = True)
    return df